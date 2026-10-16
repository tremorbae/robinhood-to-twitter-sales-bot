# Whale Street Sales Bot

Posts every sale of [Whales of WhaleStreet](https://opensea.io/collection/whalestreet)
(Robinhood Chain, `0x01f33271d74a9dcc91798c7232d3d788da93a1f6`) to X:

```
🐳 Whale Street #2863 Bought
💰 0.003849 ETH ($9.87)
🛒 OpenSea
👤 0xea0e...d9b1 → 0xb21a...2ed4
[NFT image]
```

It reads sales straight from the blockchain, so it needs no OpenSea API key. It catches
listings bought with ETH or USDG, accepted WETH offers, and sweeps.

## 1. Set up (once)

Needs [Docker](https://docs.docker.com/get-docker/).

`.env.example` lists the main settings, already filled in for Whale Street except the X keys.
Only the X keys and `DRY_RUN` need to be set: everything else has a default. Optional settings
(RPC, IPFS gateway, minimum price, ...) are listed with their defaults in `config.py`.

- **Hosting on a Docker service:** enter the settings in the host's environment variables
  page (see step 4). No `.env` file is needed.
- **Running on your own computer or server:** `cp .env.example .env`, add the X keys, then
  `docker compose build`.

## 2. Try it without posting

`DRY_RUN` defaults to `true`, so nothing is posted. Posts are printed to the logs instead.

```bash
docker compose run --rm bot python bot.py --check     # tests the RPC + contract (+ X keys once added)
docker compose run --rm bot python bot.py --tx 0x215505a66660d82426b5c9dfd5fc1e20af9977ddbcb24ccf93b4d86400c8ebbb
docker compose up                                     # watch for new sales (Ctrl+C to stop)
```

## 3. Get X API keys

1. **Create the bot's X account** (e.g. @WhaleStreetSales) and stay logged in as it.
2. Go to **developer.x.com**, sign up as that account, and **buy API credits**. Since
   February 2026 the API is pay-per-use and new accounts get no free tier. Set a spending limit.
3. Create an app (project). Under **User authentication settings**, set
   **App permissions → Read and write**. If it asks for a callback URL and website, any URL
   you own works (e.g. `http://localhost` / your project site).
4. Open **Keys and tokens** and copy these into the host's environment variables (or `.env`):
   - API Key → `X_API_KEY`, API Key Secret → `X_API_SECRET`
   - Access Token → `X_ACCESS_TOKEN`, Access Token Secret → `X_ACCESS_TOKEN_SECRET`

   Generate the Access Token **after** switching to "Read and write". A token made earlier is
   read-only and posting fails with a 403.
5. Run `docker compose run --rm bot python bot.py --check`. It should say `X: authenticated as @YourBot`.
6. Set `DRY_RUN=false` and start the bot (step 4).

**"Automated by" label** (like the reference screenshots): on the bot account, go to
Settings → Your account → Account information → **Automation**, and pick your main account
as the managing account.

**Cost:** about $0.015 per post. At the recent pace (~20 sales a day) that's roughly
$10/month. A post containing a link costs $0.20, so the template has none. To skip tiny
sales, set `MIN_PRICE_USD`.

## 4. Keep it running 24/7

The bot only posts while it's running.

**On a server with Docker** (e.g. a ~$5/month VPS):

```bash
docker compose up -d          # start in the background; restarts automatically
docker compose logs -f        # watch the logs
docker compose down           # stop
```

**On a Docker host** (Railway, Render "Background Worker", Fly.io, ...): point it at this
folder's `Dockerfile`, then:

- In the host's environment variables, set `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`,
  `X_ACCESS_TOKEN_SECRET` and `DRY_RUN` (`true` to test, `false` to post). Add any other
  setting from `.env.example` or `config.py` only if you want to change it.
- Attach a persistent volume at `/data`. The bot keeps `state.json` there: it records the
  last block scanned, so after a restart the bot catches up on missed sales and never
  double-posts. Without it, a restart starts from "now".

## Customizing

- **Post text:** edit `tweet_template.txt` (one line of the post per line, using the `{placeholders}`
  listed in `tweet.py`). With `docker compose`, a running bot uses it from its next post. On a
  hosted Docker service, redeploy to apply it.
- **Name / emoji:** `COLLECTION_NAME` and `EMOJI` settings.
- **Images:** pulled from the token metadata on IPFS. Public IPFS gateways can be slow or
  rate-limited. For faster, more reliable images, set `IPFS_GATEWAY` to a dedicated gateway
  (Pinata, Filebase) or point `IMAGE_URL_TEMPLATE` at your own image host.

## Files

| File | What it does |
|---|---|
| `bot.py` | Main loop, `--check` and `--tx` |
| `chain.py` | Reads transfers from the chain and works out sale prices from OpenSea (Seaport) orders |
| `media.py` | tokenURI → metadata → image, resized for X |
| `prices.py` | ETH/USD price (Coinbase) and token decimals |
| `tweet.py` | Fills in the post template (`tweet_template.txt`) |
| `x_client.py` | X API: image upload + post |
| `config.py` | Settings and Robinhood Chain addresses (WETH, USDG, Seaport) |
| `Dockerfile`, `docker-compose.yml` | Container build and run setup |

Tests run on real Robinhood Chain transactions saved in `tests/fixtures`
(Python 3.9+, after `pip install -r requirements.txt`):
`python -m unittest discover tests`
