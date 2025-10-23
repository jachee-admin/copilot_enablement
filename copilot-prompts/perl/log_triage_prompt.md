# Prompt: Log Triage CLI (Perl) — filter, summarize, JSON report

## Goal
Generate a robust **Perl** CLI that parses mixed application logs and produces:
- Counts by **level** (INFO/WARN/ERROR)
- Top **endpoints/messages**
- **Response-time** statistics (avg/p95) when lines contain `NNNms`
- Optional **JSON** summary output

## Context / Constraints (include with the prompt)
- Perl **5.32+**
- Core/standard modules only or widely-available:
  - `strict`, `warnings`, `utf8`, `open qw/:std :encoding(UTF-8)/`
  - `Getopt::Long` (CLI)
  - `Time::Piece` (timestamp parsing) — format `YYYY-MM-DD HH:MM:SS`
  - `JSON::PP` (JSON output)
  - Optional: `List::Util` for stats
- Input line format (typical):
```
2025-10-23 10:22:01 [INFO] Service started
2025-10-23 10:22:05 [WARN] Slow response: 420ms /api/health
2025-10-23 10:22:09 [ERROR] DB timeout /api/login user=john
2025-10-23 10:22:14 [INFO] Request completed: 210ms /api/login user=jane
```
- CLI flags:
- `--file <path>` (required)
- `--level <LEVEL>` (filter)
- `--since "YYYY-MM-DD HH:MM:SS"` (ignore older)
- `--endpoint <substr>` (filter by substring)
- `--json` (emit JSON summary, else pretty text)
- Must handle missing fields gracefully. No crashes.

## Primary Prompt (paste to Copilot)
> Write a Perl script `log_triage.pl` that:
> - Uses `use strict; use warnings; use utf8; use open qw/:std :encoding(UTF-8)/;`
> - Parses CLI flags via `Getopt::Long`:
>   `--file`, `--level`, `--since`, `--endpoint`, `--json`
> - Reads the log file line-by-line, parsing:
>   - timestamp: `YYYY-MM-DD HH:MM:SS` (with `Time::Piece`)
>   - level: `[INFO|WARN|ERROR]`
>   - response time if present: `/(\d+)ms/`
>   - endpoint substrings like `/api/...` (use a simple regex)
> - Applies filters (level, since, endpoint).
> - Computes:
>   - counts by level
>   - top 5 endpoints by count (if found)
>   - response time avg and p95 (if any)
> - If `--json`, print a JSON summary; else print a readable, aligned report.
> - On invalid `--since`, exit non-zero with a clear message.
> - Include inline comments and small helper subs.

## Acceptance Criteria
- Works with the provided format; ignores unrelated lines safely.
- Filters are all optional and composable.
- No fatal errors on missing `ms` or endpoint.
- JSON output uses `JSON::PP->new->ascii->canonical->pretty(1)`.
- Pretty text output aligns columns.

---

## Reference Implementation

```perl
#!/usr/bin/env perl
use strict;
use warnings;
use utf8;
use open qw/:std :encoding(UTF-8)/;

use Getopt::Long qw(:config bundling);
use Time::Piece;
use JSON::PP ();
use List::Util qw(sum);

my ($file, $level, $since_str, $endpoint, $json);
GetOptions(
'file=s'     => \$file,
'level=s'    => \$level,
'since=s'    => \$since_str,
'endpoint=s' => \$endpoint,
'json!'      => \$json,
) or die "Usage: $0 --file <path> [--level LEVEL] [--since 'YYYY-MM-DD HH:MM:SS'] [--endpoint /api/... ] [--json]\n";

(-f $file) or die "error: file not found: $file\n";

my $since_epoch = 0;
if (defined $since_str) {
eval {
  my $tp = Time::Piece->strptime($since_str, '%Y-%m-%d %H:%M:%S');
  $since_epoch = $tp->epoch;
  1;
} or die "error: invalid --since timestamp format (expected 'YYYY-MM-DD HH:MM:SS')\n";
}

my %level_count = ( INFO => 0, WARN => 0, ERROR => 0 );
my %endpoint_count;
my @times;

open my $fh, '<', $file or die "error: open $file: $!\n";
LINE:
while (my $line = <$fh>) {
chomp $line;

# ts + level
$line =~ m/^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[([A-Z]+)\]\s+(.*)$/ or next;
my ($ts, $lvl, $msg) = ($1, $2, $3);

if ($level && $lvl ne $level) {
  next LINE;
}

if ($since_epoch) {
  my $tp = eval { Time::Piece->strptime($ts, '%Y-%m-%d %H:%M:%S') };
  next LINE if !$tp || $tp->epoch < $since_epoch;
}

if ($endpoint && index($line, $endpoint) < 0) {
  next LINE;
}

$level_count{$lvl}++ if exists $level_count{$lvl};

# endpoint like /api/...
if ($line =~ m{(/api/[A-Za-z0-9_/\-]+)}) {
  $endpoint_count{$1}++;
}

# response time: NNNms
if ($line =~ /(\d+)ms\b/) {
  push @times, $1 + 0;
}
}
close $fh;

sub avg {
return 0 unless @times;
return sum(@times) / @times;
}
sub p95 {
return 0 unless @times;
my @s = sort { $a <=> $b } @times;
my $idx = int(0.95 * ($#s));
return $s[$idx];
}

my @top_endpoints = sort { $endpoint_count{$b} <=> $endpoint_count{$a} } keys %endpoint_count;
splice @top_endpoints, 5 if @top_endpoints > 5;

if ($json) {
my $out = {
  counts => \%level_count,
  top_endpoints => [ map { +{ endpoint => $_, count => $endpoint_count{$_} } } @top_endpoints ],
  response_time => {
    avg_ms => 0+sprintf('%.1f', avg()),
    p95_ms => 0+sprintf('%.1f', p95()),
    samples => scalar @times,
  },
};
my $j = JSON::PP->new->ascii->canonical->pretty(1);
print $j->encode($out);
} else {
printf "Level Counts:\n";
printf "  %-5s %6d\n", 'INFO',  $level_count{INFO};
printf "  %-5s %6d\n", 'WARN',  $level_count{WARN};
printf "  %-5s %6d\n", 'ERROR', $level_count{ERROR};
print  "\nTop Endpoints:\n";
if (@top_endpoints) {
  for my $ep (@top_endpoints) {
    printf "  %-20s %6d\n", $ep, $endpoint_count{$ep};
  }
} else {
  print  "  (none)\n";
}
printf "\nResponse Time:\n";
printf "  avg: %.1f ms   p95: %.1f ms   samples: %d\n", avg(), p95(), scalar @times;
}
```

### Usage
```bash
perl log_triage.pl --file app.log
perl log_triage.pl --file app.log --level ERROR --since "2025-10-23 10:22:00"
perl log_triage.pl --file app.log --endpoint /api/login --json
```

### Follow-up Refinement Prompts

- “Add NDJSON output for machine pipelines.”
- “Support gz logs using IO::Uncompress::Gunzip when file ends with .gz.”
- “Add per-hour histograms of ERROR counts.”
