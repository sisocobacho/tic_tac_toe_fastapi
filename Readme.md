# Tic Tac toe Game

## Description
Tic tac toe game using web technologies

## Features
- Tic tac toe Game web application
- Play vs Computer
- Game History
- Load and Delete previous games

## Intallation
```shell script
pip install -r requirements.txt
```
### You also can use uv. You need to have it install.

```shell script
uv sync --locked
```
or use make. See make file for all commands

```shell script
make install
```
## Run Project
```shell script
python uvicorn backend.main:app
```
or with uv
```shell script
make run
```

## Test Project
```shell script
python pytest backend/test_main.py
```
or with uv.
```shell script
make test
```
## Todo
- [x] Add game vs computer
- [x] Add db persistance
- [x] Add authentication and signup
- [ ] Add multiplayer
- [ ] Improve interface
