# RFONLINEAuction

Веб-аукцион за игровые очки для RF Online.

## Запись списка игроков в Solana

Файл `players.example.json` содержит от 1 до 50 игроков. Для каждого игрока
указываются только ник и количество очков:

```json
[
  {"nickname": "DarkKnight", "points": 150},
  {"nickname": "StormMage", "points": 200}
]
```

Скрипт сортирует список по нику и отправляет одну Memo-транзакцию с полным
компактным списком:

```json
[["DarkKnight",150],["StormMage",200]]
```

Ники и очки хранятся непосредственно в транзакции Solana. Размер компактного
списка ограничен 1000 байтами, чтобы транзакция помещалась в лимит сети.

Проверить JSON и увидеть подготовленный Memo без отправки транзакции:

```powershell
python send_points.py players.example.json --dry-run
```

Установить библиотеки и отправить одну транзакцию в Devnet:

```powershell
python -m pip install -r requirements.txt
python send_points.py players.example.json --keypair C:\path\to\devnet-keypair.json
```

Файл ключа нельзя добавлять в Git. `id.json` и `*-keypair.json` уже исключены
через `.gitignore`.
