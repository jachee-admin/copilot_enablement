Perfect — here’s a polished, drop-in **Perl config loader** artifact for your `perl/` directory.

---

## `perl/config_loader_prompt.md`

````markdown
# Prompt: Robust Config Loader (Perl) — INI + ENV overrides + UTF-8 safety

## Goal
Generate a small **Perl** module and CLI that load configuration from:
1) **Defaults** (in code)
2) **INI file** (project/config.ini or XDG locations)
3) **Environment variables** (override INI using a clear mapping)
4) **CLI `--set key=value` overrides** (highest precedence)

It should be **UTF-8 safe**, dependency-light, validate required keys, and print a helpful debug view.

## Context / Constraints (include with the prompt)
- Perl **5.32+**; modules:
  - Core/common: `strict`, `warnings`, `utf8`, `open qw/:std :encoding(UTF-8)/`, `Getopt::Long`, `FindBin`, `File::Spec`
  - CPAN but ubiquitous: `Path::Tiny`, `Config::Tiny`, `JSON::PP`
- Config file format: **INI** (via `Config::Tiny`) with optional sections.
- **Search order for INI** (first found wins):
  1) `./config.ini`
  2) `./config/config.ini`
  3) `$XDG_CONFIG_HOME/myapp/config.ini` (or `~/.config/myapp/config.ini`)
- **ENV override style:** `MYAPP__SECTION__KEY=value` (double underscore as separator).
  - No section (root) → `MYAPP__KEY=value`
- CLI: `--config <path>`, `--set key=value` (repeatable), `--dump` (print merged JSON and exit)
- Merge precedence: **CLI > ENV > INI > defaults**
- Validation: required keys `server.port (int)`, `db.dsn (str)`, `db.user (str)`
- Coercions: integers for `server.port`, booleans for `feature.flags.*` (`true/false/1/0`)

## Primary Prompt (paste to Copilot)
> Write a Perl module `lib/MyApp/Config.pm` and a CLI `bin/show-config` that:
> - Are UTF-8 safe (`use open qw/:std :encoding(UTF-8)/; use utf8;`).
> - Locate and parse an INI config using the search order described.
> - Merge defaults, INI, ENV (`MYAPP__SECTION__KEY`), and CLI `--set key=value` (highest).
> - Support dot-paths for keys in `--set` (e.g., `server.port=8080`, `db.dsn=...`).
> - Provide helpers:
>   - `load(%opts)` → returns hashref of merged config
>   - `_apply_env_overrides($cfg, $prefix='MYAPP')`
>   - `_apply_set_overrides($cfg, \@pairs)`  # pairs like ['server.port=9000']
>   - `_coerce($cfg)`  # ints/bools for known paths
>   - `_validate($cfg)`  # die with clear message on missing required keys
> - `bin/show-config`:
>   - options: `--config PATH`, `--set key=value` (repeatable), `--dump`
>   - loads config and prints JSON (`JSON::PP->new->canonical->pretty->encode`)
>   - exits non-zero on validation errors
> - Keep dependencies to `Path::Tiny`, `Config::Tiny`, `JSON::PP`.
> - Include inline comments and POD.

## Acceptance Criteria
- Correct precedence: **CLI > ENV > INI > defaults**.
- ENV mapping uses `MYAPP__SECTION__KEY` (root keys as `MYAPP__KEY`).
- Dot-path parsing for `--set` works for sectioned and root keys.
- Coercions:
  - `server.port` → integer
  - `feature.flags.*` → boolean
- Validation errors are explicit and actionable.
- `--dump` shows the **final merged** config in JSON (UTF-8 preserved).

---

## Example of a Good Output (reference implementation)

```perl
# lib/MyApp/Config.pm
package MyApp::Config;
use strict;
use warnings;
use utf8;
use open qw/:std :encoding(UTF-8)/;

use Config::Tiny;
use Path::Tiny qw/path/;
use JSON::PP ();
use File::Spec;
use Scalar::Util qw/looks_like_number/;

our $PREFIX = 'MYAPP';

my %DEFAULTS = (
  server => { host => '0.0.0.0', port => 8080 },
  db     => { dsn  => 'dbi:Pg:dbname=myapp', user => 'app', pass => '' },
  feature => { flags => { beta => 0, telemetry => 1 } },
);

sub load {
  my (%opts) = @_;
  my $prefix   = $opts{prefix}   // $PREFIX;
  my $confpath = $opts{config};           # optional explicit path
  my $sets     = $opts{set} // [];        # arrayref of "k=v"

  my $cfg = _deep_clone(\%DEFAULTS);

  # INI → merge
  if (my $ini_path = $confpath // _find_ini_path()) {
    if (-f $ini_path) {
      my $ini = Config::Tiny->read($ini_path, 'utf8');
      die "config read error: $Config::Tiny::errstr\n" unless $ini;
      _merge_ini($cfg, $ini);
      $cfg->{_meta}{source} = "$ini_path";
    }
  }

  # ENV → merge
  _apply_env_overrides($cfg, $prefix);

  # CLI --set → merge
  _apply_set_overrides($cfg, $sets);

  # Coercions & validation
  _coerce($cfg);
  _validate($cfg);

  return $cfg;
}

sub _find_ini_path {
  my @candidates = (
    path('./config.ini'),
    path('./config/config.ini'),
    _xdg_config_home()->child('myapp', 'config.ini'),
  );
  for my $p (@candidates) {
    return $p->stringify if $p && -f $p;
  }
  return; # none
}

sub _xdg_config_home {
  my $xdg = $ENV{XDG_CONFIG_HOME};
  return path($xdg) if $xdg;
  my $home = $ENV{HOME} // (getpwuid($<))[7];
  return path(File::Spec->catdir($home, '.config'));
}

sub _merge_ini {
  my ($cfg, $ini) = @_;
  # Config::Tiny structure: { _ => {k=>v}, section => {k=>v} }
  if (my $root = $ini->{_}) {
    $cfg->{$_} = _merge_hash($cfg->{$_}, $root->{$_}) for keys %$root;
  }
  for my $sec (grep { $_ ne '_' } keys %$ini) {
    $cfg->{$sec} //= {};
    my $h = $ini->{$sec};
    for my $k (keys %$h) {
      $cfg->{$sec}{$k} = $h->{$k};
    }
  }
}

sub _apply_env_overrides {
  my ($cfg, $prefix) = @_;
  for my $k (keys %ENV) {
    next unless index($k, "${prefix}__") == 0;
    my $rest = substr($k, length($prefix) + 2); # after PREFIX__
    my @parts = split /__/, $rest;
    my $val = $ENV{$k};
    _set_path($cfg, \@parts, $val);
  }
}

sub _apply_set_overrides {
  my ($cfg, $pairs) = @_;
  for my $p (@$pairs) {
    my ($path, $val) = split /=/, $p, 2;
    die "--set expects key=value, got '$p'\n" unless defined $val;
    my @parts = split /\./, $path; # dot path
    _set_path($cfg, \@parts, $val);
  }
}

sub _set_path {
  my ($root, $parts, $val) = @_;
  my $h = $root;
  for my $i (0 .. $#$parts - 1) {
    my $k = $parts->[$i];
    $h->{$k} //= {};
    die "Cannot set path: $k is not a hash\n" unless ref($h->{$k}) eq 'HASH';
    $h = $h->{$k};
  }
  $h->{ $parts->[-1] } = $val;
}

sub _coerce {
  my ($cfg) = @_;
  # ints
  $cfg->{server}{port} = int($cfg->{server}{port}) if defined $cfg->{server}{port};

  # booleans under feature.flags.*
  if (my $flags = $cfg->{feature}{flags}) {
    for my $k (keys %$flags) {
      $flags->{$k} = _to_bool($flags->{$k});
    }
  }

  return $cfg;
}

sub _to_bool {
  my ($v) = @_;
  return 0 unless defined $v;
  my $s = lc("$v");
  return 1 if $s eq '1' || $s eq 'true'  || $s eq 'yes' || $s eq 'on';
  return 0 if $s eq '0' || $s eq 'false' || $s eq 'no'  || $s eq 'off';
  return $v =~ /^\d+$/ ? ($v != 0) : !!$v; # fallback
}

sub _validate {
  my ($cfg) = @_;
  my @missing;
  push @missing, 'server.port' unless defined $cfg->{server}{port};
  push @missing, 'db.dsn'      unless defined $cfg->{db}{dsn} && length $cfg->{db}{dsn};
  push @missing, 'db.user'     unless defined $cfg->{db}{user} && length $cfg->{db}{user};
  die "config validation failed: missing ".join(', ', @missing)."\n" if @missing;
}

sub _merge_hash {
  my ($old, $new) = @_;
  return $new unless ref($old) eq 'HASH' && ref($new) eq 'HASH';
  my %m = (%$old, %$new);
  return \%m;
}

sub _deep_clone {
  my ($r) = @_;
  if (ref($r) eq 'HASH') { return { map { $_ => _deep_clone($r->{$_}) } keys %$r } }
  if (ref($r) eq 'ARRAY'){ return [ map _deep_clone($_), @$r ] }
  return $r;
}

1;

__END__

=pod

=head1 NAME

MyApp::Config - INI + ENV + CLI config loader with UTF-8 safety

=head1 SYNOPSIS

  use MyApp::Config;
  my $cfg = MyApp::Config::load();

=head1 ENV OVERRIDES

Prefix (default C<MYAPP>) and double-underscore separators:

  MYAPP__server__port=9000
  MYAPP__db__dsn='dbi:Pg:dbname=prod'
  MYAPP__feature__flags__beta=true

=cut
````

```perl
# bin/show-config
#!/usr/bin/env perl
use strict;
use warnings;
use utf8;
use open qw/:std :encoding(UTF-8)/;

use Getopt::Long qw/:config bundling/;
use JSON::PP ();
use FindBin;
use lib "$FindBin::Bin/../lib";
use MyApp::Config ();

my ($config_path, @sets, $dump);
GetOptions(
  'config=s' => \$config_path,
  'set=s@'   => \@sets,        # repeatable --set key=value
  'dump!'    => \$dump,
) or die "Usage: $0 [--config PATH] [--set k=v ...] [--dump]\n";

my $cfg = MyApp::Config::load(
  config => $config_path,
  set    => \@sets,
);

my $json = JSON::PP->new->canonical->pretty->encode($cfg);
print $json;

exit 0;
```

### Example `config.ini`

```ini
[server]
host=127.0.0.1
port=8081

[db]
dsn=dbi:Pg:dbname=myapp_dev
user=dev
pass=devpass

[feature.flags]
beta=true
telemetry=false
```

### Usage

```bash
# 1) Defaults + discovered INI (./config.ini or ./config/config.ini or XDG)
perl bin/show-config

# 2) Explicit file and CLI overrides
perl bin/show-config --config ./config.ini --set server.port=9000 --set feature.flags.telemetry=on

# 3) ENV overrides (highest after --set)
export MYAPP__db__user=service
export MYAPP__feature__flags__beta=false
perl bin/show-config --dump
```

### Notes & Pitfalls

* `Config::Tiny` flattens sections; keys like `[feature.flags]` are still fine (we treat the literal section name as level-1 in the hash).
* ENV mapping is **case-sensitive** here; keep names consistent.
* If you later want nested sections (e.g., `feature.flags.*`) mapped hierarchically from INI, switch to `Config::INI::Reader` and adapt `_merge_ini`.

### Follow-up Refinement Prompts

* “Add schema validation with `Type::Tiny` or `Specio`.”
* “Support YAML configs if `YAML::XS` is available; fallback to INI.”
* “Add `--profile prod/dev` to switch config files quickly.”
* “Encrypt secrets at rest with `GnuPG` and a `--decrypt` hook for CI.”

```

---

Want a quick unit test (`t/config.t`) to assert precedence and coercions, or move on to the remaining SQL/Bash files?
```
