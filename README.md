# selkokortti
Generate Anki flashcards from [Andrew's Selkouutiset Archive](https://hiandrewquinn.github.io/selkouutiset-archive/).

[recording.webm](https://github.com/Selkouutiset-Archive/selkokortti/assets/53230903/15485a58-725a-4d79-8a2c-59da04c65448)


## Quickstart

`selkokortti` is packaged for [`uv`](https://docs.astral.sh/uv/). Install it as a
tool and you get a `selkokortti` binary that **fetches the latest news data for
you** — no submodules, no manual cloning:

```bash
uv tool install git+https://github.com/Selkouutiset-Archive/selkokortti

selkokortti --help
selkokortti range 2025.06.20 2025.06.23     # cards for June 20–23, 2025, inclusive
```

![image](https://github.com/Selkouutiset-Archive/selkokortti/assets/53230903/93242673-2dde-4373-b1d2-fcb24a37a0f5)

On first run it clones the [Selkouutiset data
repo](https://github.com/hiAndrewQuinn/selkouutiset-scrape-cleaned) into your
user cache directory, and refreshes it on every subsequent run. A file called
`cards.apkg` appears in your current directory — import it into Anki and start
going through the new `Selko` deck.

You can also run it without installing, or hack on it locally:

```bash
git clone https://github.com/Selkouutiset-Archive/selkokortti
cd selkokortti
uv run selkokortti --help            # uv sets up the environment automatically
```

### Commands and options

| Command | What it does |
| --- | --- |
| `range yyyy.mm.dd yyyy.mm.dd` | Cards for an inclusive date range (most flexible). |
| `latest [N]` | Cards for the N most recent available dates (default 7). |
| `today` | Cards for today's date. |
| `everything` | Cards for every available date. |
| `info` | Show the dataset cache location and the available date range. |

Run `selkokortti --version` to print the version, or `selkokortti <command> --help`
for a command's full options.

Shared options (on the card-generating commands):

- `--direction / -d` — `fi-en` (Finnish prompt → English, the default),
  `en-fi` (English prompt → Finnish, for active production practice), or
  `both` (one note, two linked cards in both directions).
- `--output` — output filename (default `cards.apkg`).
- `--deck-name` — name of the generated Anki deck (default `Selko`).
- `--data-dir PATH` — use a local checkout of `selkouutiset-scrape-cleaned`
  instead of the auto-managed cache (skips all network access).
- `--no-update` — reuse the cached dataset without refreshing it.
- `--verbose / -v`, `--quiet / -q` — log verbosity (`-v` also shows raw `git` output).

```bash
selkokortti latest 7                                 # last 7 days of articles
selkokortti range 2025.06.20 2025.06.23 -d both      # bidirectional cards
selkokortti range 2025.06.20 2025.06.23 -d en-fi     # English → Finnish production
selkokortti info                                     # what dates are available?
```

If you ask for a date with no article (a weekend or a date that hasn't happened
yet), `selkokortti` tells you so and points you at the most recent available date
instead of failing cryptically.

![image](https://github.com/Selkouutiset-Archive/selkokortti/assets/53230903/07c80715-4d04-4012-8f06-6613824f9216)

Then you can import the `cards.apkg` to Anki, and start going through the new `Selko` deck it creates.

If you wish to inspect the `cards.apkg` yourself before importing it, `unzip` it and load the resulting `collections.anki2` into a SQLite viewer, as below:

![image](https://github.com/Selkouutiset-Archive/selkokortti/assets/53230903/cf272cfa-f647-42df-8cd2-790dc2d60ef1)

## Slowstart

For folks who don't, I'm going to use the [tutorial-in-a-box technique](https://hiandrewquinn.github.io/til-site/posts/the-unreasonable-effectiveness-of-vms-in-hacker-pedagogy/) to help you get started. My hope is that after you run this, you'll be able to figure out how to install it yourself if you want to, wherever you want to.

You'll need [Virtualbox](https://www.virtualbox.org/) (it makes virtual machines, basically little computer inside your computer) and [Vagrant](https://www.vagrantup.com/) (it lets us use VB from the command line). You can get stable versions of these on Linux, Windows, BSD, and (non-ARM) Macs.

First run

```bash
mkdir tutorial/
cd tutorial/

vagrant init debian/bookworm64
vagrant up
vagrant ssh
```

You can exit this Linux virtual machine at any time with `exit`, and destroy it completely with

```
vagrant destroy --force
```

. Going back into `tutorial/` and running `vagrant up` will recreate it from scratch as if nothing happened, and running `vagrant ssh` will put you back in the VM.

Let's install everything we need. `apt` lets us install things on Debian from the command line, and [`uv`](https://docs.astral.sh/uv/) is the Python tool installer we'll use.

```bash
sudo apt update -y
sudo apt install git curl -y

curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

Next run

```bash
uv tool install git+https://github.com/Selkouutiset-Archive/selkokortti
```

to install the `selkokortti` command. If you get asked something like `Are you sure you want to continue connecting (yes/no/[fingerprint])?`, answer `yes`.

You should now see a fancy help text appear when you run

```bash
selkokortti --help
```

The actual news data comes from [this other repo](https://github.com/hiAndrewQuinn/selkouutiset-scrape-cleaned), but you don't have to fetch it yourself — `selkokortti` downloads and updates it for you automatically the first time you run it.

Now, finally, you can generate your flashcard Anki deck with e.g.

```bash
selkokortti range 2024.02.01 2024.02.05    # Flashcards from February 1st to 5th, 2024, inclusive.
```

A file called `cards.apkg` will appear in your current directory, which you can see by running `ls`. *This is what you want for Anki.* Getting to the point where you generate this `cards.apkg` is on you, but hopefully this Slowstart helps you see everything you need to do to get there, regardless of your experience level.
