# Linear CLI

Simple CLI interface for linear task manager (https://linear.app)


## Usage

### Install:

```
pip install linearcli
```

or if you want to hack on it (please do)

```
pip install -e path/to/where/you/checked/out/the/repo
```

### Setup:

Generate a personal API key in the linear app, and run `linear init <apikey>`

This will create `~/.linear/data.json

### Sync:

The CLI tool creates a local cache of slowly changing data (teams, users,
task states, avatars), you can update the cache by doing `linear sync`

### Help:

```
$ linear --help
```
