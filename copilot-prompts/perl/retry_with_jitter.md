# Prompt: Exponential Backoff + Full Jitter (Perl) — module + examples

## Goal
Generate a small, dependency-light **Perl** module that wraps operations with **bounded retries**, **exponential backoff**, and **full jitter** — with hooks for logging and selective exception retry.

## Context / Constraints
- Perl **5.32+**
- Modules: core where possible:
  - `strict`, `warnings`, `utf8`, `open qw/:std :encoding(UTF-8)/`
  - `Time::HiRes` for sub-second sleeps
  - `Scalar::Util 'blessed'` to inspect exception objects
  - Optional: `Try::Tiny` for clean try/catch (allowed)
- API requirements:
  - Function-style helper: `retry( sub { ... }, \%opts )`
  - Options (defaults shown):
    - `max_attempts => 5`
    - `base_delay  => 0.25`  (seconds)
    - `max_delay   => 8.0`
    - `retry_if    => sub ($err) { 1 }`  (predicate)
    - `on_retry    => sub ($attempt,$err,$sleep_s) { }`
  - Backoff: `delay = min(max_delay, base_delay * 2**(attempt-1))`
  - Jitter: sleep `rand() * delay`
  - Re-raise last error on exhaustion
  - Document **NOT** catching `SIGINT`/`SIGTERM` inadvertently

## Primary Prompt (paste to Copilot)
> Write `lib/Retry/Jitter.pm` implementing:
> - `retry($code, \%opts)` with the options above.
> - A private `_sleep($seconds)` using `Time::HiRes::sleep`.
> - Use `Try::Tiny` if available; otherwise `eval { ... }`.
> - Do not swallow non-retryable exceptions; rethrow immediately.
> - Include POD, type-ish checks, and examples.
> Also provide an example script `examples/retry_demo.pl` showing:
> - Retrying a flaky HTTP call placeholder
> - Logging via `on_retry`
> - Custom predicate that retries only for `RuntimeError`-like messages

## Acceptance Criteria
- Deterministic parameters; jitter randomness is the only RNG.
- Clean separation of **policy** vs **action**.
- Final failure rethrows the last error (preserve message).
- Works without non-core modules (fallback path when `Try::Tiny` missing).
- Unit-test-friendly: `on_retry` fires before sleep; can be used to assert.

---

## Reference Module + Demo

```perl
# lib/Retry/Jitter.pm
package Retry::Jitter;
use strict;
use warnings;
use utf8;
use Time::HiRes qw(sleep);
use Scalar::Util qw(blessed);

our $VERSION = '0.01';

sub retry {
  my ($code, $opt) = @_;
  die "retry: code ref required" unless ref($code) eq 'CODE';
  $opt ||= {};

  my $max_attempts = $opt->{max_attempts} // 5;
  my $base_delay   = $opt->{base_delay}   // 0.25;
  my $max_delay    = $opt->{max_delay}    // 8.0;
  my $retry_if     = $opt->{retry_if}     // sub { 1 };
  my $on_retry     = $opt->{on_retry};

  my $attempt = 0;
  my $last_err;

  while ($attempt < $max_attempts) {
    my ($ok, $ret) = _try($code);
    if ($ok) {
      return $ret;
    } else {
      $last_err = $ret; # $@
      $attempt++;

      # Decide if we retry
      my $do_retry = eval { $retry_if->($last_err) } // 0;
      if (!$do_retry || $attempt >= $max_attempts) {
        die $last_err;
      }

      my $delay = $base_delay * (2 ** ($attempt - 1));
      $delay = $max_delay if $delay > $max_delay;
      my $sleep_s = rand() * $delay;

      eval { $on_retry->($attempt, $last_err, $sleep_s) } if $on_retry;

      sleep($sleep_s);
    }
  }
  die $last_err;
}

sub _try {
  my ($code) = @_;
  my ($ok, $ret);
  # Try::Tiny optional
  eval {
    $ret = $code->();
    $ok  = 1;
    1;
  } or do {
    $ok  = 0;
    $ret = $@;
  };
  return ($ok, $ret);
}

1;

__END__

=pod

=head1 NAME

Retry::Jitter - Exponential backoff with full jitter for transient errors

=head1 SYNOPSIS

  use Retry::Jitter qw/retry/;

  my $val = retry(sub {
      die "Transient" if rand() < 0.7;
      return "OK";
  }, {
      max_attempts => 4,
      on_retry     => sub { my ($n,$err,$sleep)=@_; warn "attempt $n: $err (sleep $sleep s)\n" },
      retry_if     => sub ($err) { "$err" =~ /Transient|timeout|5\d\d/ },
  });

=head1 DESCRIPTION

Implements bounded retries with exponential backoff and full jitter.
Accepts a predicate to decide which errors are retryable.

=head1 OPTIONS

=over 4

=item * max_attempts (Int)

=item * base_delay, max_delay (Seconds, Num)

=item * retry_if (CodeRef) — gets C<$err>, return true to retry

=item * on_retry (CodeRef) — called before sleep

=back

=cut
```

```perl
# examples/retry_demo.pl
#!/usr/bin/env perl
use strict;
use warnings;
use utf8;
use lib 'lib';
use Retry::Jitter qw/retry/;

$|=1;

my $attempts = 0;

my $res = eval {
  retry(sub {
    $attempts++;
    if (rand() < 0.7) { die "Transient failure on attempt $attempts\n" }
    return "SUCCESS on attempt $attempts";
  }, {
    max_attempts => 5,
    base_delay   => 0.2,
    max_delay    => 2.0,
    on_retry     => sub {
      my ($n,$err,$sleep) = @_;
      printf STDERR "retry #%d: %sSleeping %.2fs...\n", $n, $err, $sleep;
    },
    retry_if     => sub ($err) {
      $err =~ /Transient|timeout|5\d\d/;
    },
  });
};

if ($@) {
  warn "Operation failed: $@";
  exit 1;
} else {
  print "$res\n";
}

```

### Usage
```bash
perl -Ilib examples/retry_demo.pl
```
### Follow-up Refinement Prompts

- “Add an async variant using AnyEvent or IO::Async timers.”
- “Add decorator-style sugar via Sub::Wrap for existing subs.”
- “Record metrics (attempt count, total sleep) via a callback.”
- “Make RNG injectable for deterministic tests.”
