# `spline`

`spline` is a shell-friendly DSL for writing `sed(1)`-like Python one-liners.

You can think of it as an efficient (but limited) mini-language for common data
processing tasks.  It's efficient because it's often much shorter than writing
the equivalent Python (or other) program, but limited because it's only useful
for expressing a certain class of progams.

Internally, the `spline` mini-language is converted into a Python program that
is immediately executed (though it's possible to dump it for debugging, or to
use as a scaffolding for a more complex program). The Python program is
constructed as a chain of generator expressions -- starting with a generator
that produces lines from stdin, data is fed through each expression, and
ultimately the generator is materialized at the end of the program, where its
contents are written to stdout.

`spline` is not meant to replace the usual UNIX text-processing tools. Instead,
it's meant to bridge the gap between shell command and program, letting you tap
into the flexibility of Python without having to break out your editor.

## Quick start

    wget https://github.com/hut8labs/spline
    chmod +x spline
    ./spline --list

The `--list` option shows a formatted grouping of the available spline
commands, along with the arguments they take and a brief description of the
command.

## Examples

* Print the next 30 days that are Mondays or Fridays.

        seq 30 | spline -a 'today=date.today()' to_int map 'today + timedelta(days=_)' filter '_.weekday() in (0, 5)'

* Count the weekdays between now and March 1st.

        spline const 'date.today()' iterate '_ + timedelta(days=1)' filter '_.weekday() <= 5' takewhile '_ < date(2015, 3, 1)' | wc -l

* Sum expenses from a CSV file. Drops the first line with column names, removes
  records that column 2 indicates are non expenses, extracts column 3, and sums.

        dump-csv.sh | spline skip 1 to_csv filter '_[1].lower().startswith("expenses")' map '_[2]' to_int sum

* Count files by extension:

        find . -type f | ./spline -3 paths sortby '_.suffix' groupby '_.suffix' map '_[0], len(list(_[1]))'

* Rewrite "JSON log" files containing one JSON object per line:

        dump-json-records.sh | spline from_json map '_["root_dir"] += "/subdir"' to_json


## Convenient features

### Automatic imports

As `spline` reads your program, it scans it for the names of Python modules,
and automatically imports those modules. This way, you can say

    spline dropwhile 're.search("^[0-9]+", _)' 

without having to import the `re` module explicitly. (This is possibly the only
time that `spline` favors implicitness, in this case so it can be much more
concise.)

### Revealing the generated Python program

The `--source` option can be used to make `spline` dump the Python program it
generates. This is useful to see what it's doing under the hood, and it can
also be used as the starting point for a full-fledged Python program when the
task at hand exceeds `spline`'s capabilities.

### Python version support

`spline` will execute using your default Python by default, but with the `-2`,
`-3`, and `-o` options, it will re-exec itseful using `python2`, `python3`, and
`pypy` respectively (provided that you have these installed on your system).

These options are useful when you want to (for example) quickly utilize Python
3's excellent `pathlib` module, or need the performance boost that Pypy can
often provide.

### Error reporting

`spline` keeps track of which commands and arguments correspond to which lines
in the Python program it generates and runs, so that syntax and runtime errors
can be tracked back to command/arguments in which they originated. For example:

    seq 10 | ./spline sum

In this program, we've forgotten to convert the input lines to integers first,
so when we run the program, we see:

    Runtime error: unsupported operand type(s) for +: 'int' and 'str' (in "sum")

In cases where `spline` can't figure out where the error originated, you'll
currently see a (usually short) Python stacktrace.

### Variable definitions

The `-a`/`--assign` option allows you to make variable assignments that occur
before the generator expressions are run. This allows you to pull values out
and make them easier to manipulate at the end of your command line:

    get-deadlines.sh | spline to_date filter '_ < VACATION' from_date -a VACATION='date(2015, 7, 1)'

Editing the value of VACATION is now easier than it would be if the date was
embedded in the filter expression.


## The `spline` mini-language

### Chaining generators

`spline` provides an efficient way to generate and run a subset of Python
programs -- specifically, those in which data is fed from standard input
through a series of Python generator expressions. Programs like these (not
coincidentally) closely resemble passing data through a series of programs in a
shell pipeline.

If you're not familiar with them, Python generators are special kinds of
functions and expressions that produce values *on demand* -- unlike, say, a
function that produces a list of values and returns the list. Series of
connected generators, much like series of connected shell programs, are ideal
for clearly expressing multi-step transformations of data.

Ideal as Python generators are for processing data, some scaffolding is
required in order to use them efficiently in a shell environment -- imports,
reading from stdin, writing to stdout, handling errors. This scaffolding is
effectively what `spline` provides, along with syntatic sugar for writing
generators for common data-processing tasks.

### Syntax

A program written in the `spline` DSL is read from left to right. When a
command that `spline` understands is encountered, the compiler consumes the
arguments for that command. When all commands and arguments have been consumed,
`spline` generates a Python program and runs it. (You can always see this
program, instead of running it, via `spline [your program] --source`).

Consider the following program:

    seq 20 | spline to_int map '_ * _' sum

`spline` processes it as follows:

1. `to_int` is a `spline` command, and it takes no arguments
1. `map` is a 1-argument command, so we consume the next argument (`'_ * _'`)
1. `sum` also takes no arguments
1. Having read a program with three commands, `spline` internally generates a
   program that looks roughly as follows, and runs it:

        import os
        import sys
        _v_000 = (_.rstrip() for _ in sys.stdin)
        _v_001 = (int(_) for _ in _v_000)
        _v_002 = ((_ * _) for _ in (_v_001))
        _v_003 = sum(_v_002)
        try:
            if hasattr(_v_003, "__iter__"):
                for _ in _v_003:
                    print(_)
            else:
                print(_v_003)
        except IOError as e:
            if e.errno != 32: raise


### Bind variables

Many `spline` commands take an expression that is evaluated in some way to
transform the input. For example, `map` generates a series of values by
evaluating an expression for each input value, just like Python list
comprehensions or the `map` function in many programming languages.

The "bind variable" in `spline` is used to represent each input value, and
every `spline` command uses the bind variable in its own way. `map`, for
example, evaluates the expression for each input using the bind variable, and
passes the resulting values to the next command; `filter` also evaluates the
expression for each input using the bind variable, but discards the values for
which the expression is equal to `false`.

Currently `reduce` is an exceptional case, as it requires two variables: one
for the previous result of `reduce` and one for the current value. It uses `_1`
and `_2` for these respectively.

`spline` allows you to set the bind variable's name using `-b`/`--bind`, so you
can say:

    spline -b line map 'line.strip()'


## Where we're headed

We're still trying to figure out what does and doesn't work, so expect some
changes to the set of built-in commands -- and potentially some kind of
contrib/library mechanism -- as the project evolves.

We'd love to hear what you think. Drop us a line at <info@hut8labs.com>.
