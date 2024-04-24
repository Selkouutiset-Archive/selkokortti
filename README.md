# selkokortti
Generate Anki flashcards from [Andrew's Selkouutiset Archive](https://hiandrewquinn.github.io/selkouutiset-archive/).

[recording.webm](https://github.com/Selkouutiset-Archive/selkokortti/assets/53230903/15485a58-725a-4d79-8a2c-59da04c65448)


## Quickstart

For people who more or less know what they're doing:

```bash
pip install typer genanki

git clone https://github.com/Selkouutiset-Archive/selkokortti
cd selkokortti
git submodule update --init --remote

python main.py --help
```

![image](https://github.com/Selkouutiset-Archive/selkokortti/assets/53230903/93242673-2dde-4373-b1d2-fcb24a37a0f5)

The most flexible way to use this is with `range yyyy.mm.dd yyyy.mm.dd`, which will create flashcards from between those dates, inclusive:

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

Let's install everything we need. `apt` lets us install things on Debian from the command line.

```bash
sudo apt update -y
sudo apt install git python3-pip -y

pip3 install typer genanki --break-system-packages

export PATH="$PATH:/home/vagrant/.local/bin"
```

Next run

```bash
git clone https://github.com/Selkouutiset-Archive/selkokortti

cd selkokortti/
```

to clone this repo and go inside its folder. If you get asked something like `Are you sure you want to continue connecting (yes/no/[fingerprint])?`, answer `yes`.

You should now see a fancy help text appear when you run

```bash
python3 main.py --help
```

But we still need the actual data for our flashcards, which comes from [this other repo](https://github.com/hiAndrewQuinn/selkouutiset-scrape-cleaned). So run 

```bash
git clone https://github.com/hiAndrewQuinn/selkouutiset-scrape-cleaned.git selkouutiset-scrape-cleaned/
```

to get the latest data.

Now, finally, you can generate your flashcard Anki deck with e.g.

```bash
python3 main.py range 2024.02.01 2024.02.05    # Flashcards from February 1st to 5th, 2024, inclusive.
```

A file called `cards.apkg` will appear in your current directory, which you can see by running `ls`. *This is what you want for Anki.* Getting to the point where you generate this `cards.apkg` is on you, but hopefully this Slowstart helps you see everything you need to do to get there, regardless of your experience level.
