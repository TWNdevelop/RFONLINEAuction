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

Скрипт сортирует список по нику, создаёт канонический JSON и рассчитывает его
SHA-256. В Solana Devnet отправляется одна Memo-транзакция вида:

```text
RFOA1:<SHA-256 списка>
```

Полный список остаётся в JSON-файле. Любое изменение ника или очков изменит хеш,
поэтому файл можно проверить по записи в блокчейне.

Проверить JSON и увидеть хеш без отправки транзакции:

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
