# Linear CLI

Simple CLI interface for linear task manager (https://linear.app)


## Usage

### Install:
Frenchie4111 still owns this on the main repo. For now, you can use editable installs.

If you want to hack on it (please do)

```sh
$ git clone https://github.com/justinabrahms/linearcli.git
$ pip install -e linearcli/
```
### Setup:

Generate a personal API key in the linear app, and run `linear init <apikey>`

This will create `~/.linear/data.json

### Sync:

The CLI tool creates a local cache of slowly changing data (teams, users,
task states, avatars), you can update the cache by doing `linear sync`

### Usage

```
$ linear search foo
$ linear info tes-41
$
```
