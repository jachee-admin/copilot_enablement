## Sample Test Script for perl/config_loader_prompt.pl

```perl
#!/usr/bin/env perl
use strict;
use warnings;
use utf8;
use open qw/:std :encoding(UTF-8)/;

use Test2::V0 -no_srand => 1;
use FindBin ();
use lib "$FindBin::Bin/../lib";

use Path::Tiny qw/path tempdir tempfile/;
use File::Temp qw/tempdir/;

use MyApp::Config ();

sub slurp_json { $_[0] } # placeholder if you decide to emit JSON later

# --- Test scaffolding helpers -------------------------------------------------

sub write_ini {
  my ($path, $content) = @_;
  path($path)->parent->mkpath;
  path($path)->spew_utf8($content);
  return $path;
}

sub with_env (&) {
  my ($code) = @_;
  my %backup = %ENV;
  my $ok = eval { $code->(); 1 };
  my $err = $@;
  %ENV = %backup;
  die $err unless $ok;
}

# --- 0) Defaults only ---------------------------------------------------------

subtest 'defaults only' => sub {
  with_env {
    delete @ENV{grep /^MYAPP__/, keys %ENV};

    my $cfg = MyApp::Config::load();

    is $cfg->{server}{host}, '0.0.0.0', 'default host';
    is $cfg->{server}{port}, 8080,      'default port (int)';

    is $cfg->{db}{dsn},  'dbi:Pg:dbname=myapp', 'default db dsn';
    is $cfg->{db}{user}, 'app',                 'default db user';

    # booleans coerced
    is $cfg->{feature}{flags}{beta},      0, 'beta false';
    is $cfg->{feature}{flags}{telemetry}, 1, 'telemetry true';
  }
};

# --- 1) INI overrides ---------------------------------------------------------

subtest 'INI overrides (explicit path)' => sub {
  with_env {
    my $dir = tempdir(CLEANUP => 1);
    my $ini = write_ini("$dir/config.ini", <<'INI');
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
INI

    my $cfg = MyApp::Config::load(config => $ini);

    is $cfg->{server}{host}, '127.0.0.1', 'server.host from INI';
    is $cfg->{server}{port}, 8081,        'server.port coerced to int';
    is $cfg->{db}{dsn},      'dbi:Pg:dbname=myapp_dev', 'dsn from INI';
    is $cfg->{db}{user},     'dev',                      'user from INI';
    is $cfg->{feature}{flags}{beta},      1, 'beta true → 1';
    is $cfg->{feature}{flags}{telemetry}, 0, 'telemetry false → 0';
  }
};

# --- 2) ENV overrides > INI ---------------------------------------------------

subtest 'ENV overrides beat INI' => sub {
  with_env {
    my $dir = tempdir(CLEANUP => 1);
    my $ini = write_ini("$dir/config.ini", <<'INI');
[server]
port=8081
INI

    # ENV should win over INI
    $ENV{MYAPP__server__port} = 9001;

    my $cfg = MyApp::Config::load(config => $ini);
    is $cfg->{server}{port}, 9001, 'ENV wins over INI';
  }
};

# --- 3) CLI --set overrides > ENV > INI > defaults ----------------------------

subtest 'CLI --set wins over ENV' => sub {
  with_env {
    my $dir = tempdir(CLEANUP => 1);
    my $ini = write_ini("$dir/config.ini", <<'INI');
[server]
port=7000

[feature.flags]
beta=false
telemetry=false
INI

    $ENV{MYAPP__server__port} = 8000;           # should be overridden by --set
    $ENV{MYAPP__feature__flags__beta} = 'true'; # overridden by --set below

    my $cfg = MyApp::Config::load(
      config => $ini,
      set    => [
        'server.port=9100',
        'feature.flags.beta=false',
        'db.user=dév',  # UTF-8 check
      ],
    );

    is $cfg->{server}{port}, 9100, 'CLI --set beats ENV and INI';
    is $cfg->{feature}{flags}{beta}, 0, 'CLI sets beta=false (coerced)';
    is $cfg->{feature}{flags}{telemetry}, 0, 'existing INI telemetry=false';
    is $cfg->{db}{user}, "dév", 'UTF-8 preserved in values';
  }
};

# --- 4) Validation errors -----------------------------------------------------

subtest 'validation error when required keys missing' => sub {
  with_env {
    my $dir = tempdir(CLEANUP => 1);

    # Missing db.user and db.dsn → should die
    my $ini = write_ini("$dir/config.ini", <<'INI');
[server]
port=9000
INI

    like(
      dies { MyApp::Config::load(config => $ini) },
      qr/config validation failed: .*db\.dsn.*db\.user/s,
      'dies with clear message listing missing keys'
    );
  }
};

# --- 5) XDG discovery order ---------------------------------------------------

subtest 'XDG discovery order (no explicit path)' => sub {
  with_env {
    my $xdg   = tempdir(CLEANUP => 1);
    my $home  = tempdir(CLEANUP => 1);
    local $ENV{XDG_CONFIG_HOME} = $xdg;
    local $ENV{HOME}            = $home;

    # Place file in ./config/config.ini and also in XDG; cwd = tempdir
    my $cwd = tempdir(CLEANUP => 1);
    my $cfgdir_local = path($cwd, 'config'); $cfgdir_local->mkpath;
    my $cfg_local = write_ini($cfgdir_local->child('config.ini'), <<'INI');
[server]
port=1111
INI
    # XDG one should be ignored because local ./config/config.ini wins first
    my $cfg_xdg = write_ini(path($xdg, 'myapp', 'config.ini'), <<'INI');
[server]
port=2222
INI

    # Run from $cwd so search order picks ./config/config.ini
    my $old = path('.')->absolute;
    chdir $cwd or die "chdir: $!";

    my $cfg = MyApp::Config::load();
    is $cfg->{server}{port}, 1111, './config/config.ini wins over XDG';

    chdir $old or die "chdir back: $!";
  }
};

done_testing;
```
### Run It
```bash
prove -lv t/config.t
```
### What this covers:

- Precedence: CLI > ENV > INI > defaults
- Coercions: server.port → int; feature.flags.* → booleans
- Validation error messaging when required keys are missing
- UTF-8 handling on values
- XDG discovery order (prefers ./config/config.ini over XDG)
