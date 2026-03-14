# Integration Testing

## Prerequisites

Start the server with docker compose (uses `~/Desktop/yt-music` as the default `MEDIA_ROOT`). Choose your own API key:

```sh
API_KEYS=mysecretkey docker compose up
```

Multiple keys are comma-separated:

```sh
API_KEYS=key1,key2 docker compose up
```

Set shell variables for all examples below:

```sh
TOKEN=mysecretkey
BASE=http://localhost:6567
```

---

## LAN Access from a Browser

The server binds to `0.0.0.0` via docker compose port mapping (`6567:6567`), so it's accessible from any machine on your LAN out of the box.

**1. Find the server's LAN IP** (run on the host machine):

```sh
hostname -I | awk '{print $1}'
```

Example result: `192.168.1.42`

**2. URL format** — open in a browser on another machine:

```
http://192.168.1.42:6567/objects/
```

> **Note:** From the host machine itself, always use `localhost` instead of the LAN IP. Docker's port publishing uses iptables DNAT rules that don't apply to traffic originating from the host to its own LAN IP, so `192.168.1.42` is only reliable from *other* machines on your LAN.

**3. Setting the Bearer token in a browser** — browsers can't set `Authorization` headers during navigation, so use one of:

- **ModHeader** (Chrome/Firefox extension): add header `Authorization: Bearer <your-key>`
- **Requestly** (alternative extension)
- **Browser devtools** — use the Fetch API in the console:
  - **Browser on the host machine** — use `localhost`:
    ```js
    fetch('http://localhost:6567/objects/', { headers: { Authorization: 'Bearer mysecretkey' } })
      .then(r => r.json()).then(console.log)
    ```
  - **Browser on another LAN machine** — use the LAN IP:
    ```js
    fetch('http://192.168.1.42:6567/objects/', { headers: { Authorization: 'Bearer mysecretkey' } })
      .then(r => r.json()).then(console.log)
    ```

**4. From another machine with curl** (non-browser alternative):

- **From the host machine:**
  ```sh
  curl -s "http://localhost:6567/objects/" -H "Authorization: Bearer $TOKEN"
  ```
- **From another LAN machine:**
  ```sh
  TOKEN=mysecretkey
  BASE=http://192.168.1.42:6567
  curl -s "$BASE/objects/" -H "Authorization: Bearer $TOKEN"
  ```

---

## 1. GET /info

**Happy path — expect 200 + JSON body**

```sh
curl -s "$BASE/info" -H "Authorization: Bearer $TOKEN"
```

Expected: `{"message":"hello world"}`

**Missing token — expect 401**

```sh
curl -s -o /dev/null -w "%{http_code}" "$BASE/info"
```

Expected: `401`

---

## 2. GET /objects/{path} — list or retrieve

The path determines behaviour: a directory path returns a JSON listing; a file path streams file content.

**Root listing — expect 200 + JSON array**

```sh
curl -s "$BASE/objects/" -H "Authorization: Bearer $TOKEN"
```

Expected: JSON array of entries at the root of `MEDIA_ROOT`.

**Subdir listing via path — expect 200 + filtered results**

```sh
curl -s "$BASE/objects/movies" -H "Authorization: Bearer $TOKEN"
```

Expected: JSON array containing only entries under the `movies/` directory.

**Recursive — expect 200 + nested entries**

```sh
curl -s "$BASE/objects/?recursive=true" -H "Authorization: Bearer $TOKEN"
```

Expected: JSON array of all entries under `MEDIA_ROOT`, including subdirectories.

**Unknown path — expect 404**

```sh
curl -s -o /dev/null -w "%{http_code}" "$BASE/objects/does-not-exist" \
  -H "Authorization: Bearer $TOKEN"
```

Expected: `404`

**Missing token — expect 401**

```sh
curl -s -o /dev/null -w "%{http_code}" "$BASE/objects/"
```

Expected: `401`

---

## 3. GET /objects/{path} — file retrieval

**Full download — expect 200 + file body**

```sh
curl -s "$BASE/objects/movies/sample.mp4" -H "Authorization: Bearer $TOKEN" -o sample.mp4
```

Expected: status 200, `Accept-Ranges: bytes` header, file written to `sample.mp4`.

**Partial download with Range header — expect 206 + Content-Range**

```sh
curl -i "$BASE/objects/movies/sample.mp4" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Range: bytes=0-1023"
```

Expected: status `206 Partial Content`, header `Content-Range: bytes 0-1023/<total>`, 1024 bytes in body.

**Missing file — expect 404**

```sh
curl -s -o /dev/null -w "%{http_code}" "$BASE/objects/does-not-exist.mp4" \
  -H "Authorization: Bearer $TOKEN"
```

Expected: `404`

**Missing token — expect 401**

```sh
curl -s -o /dev/null -w "%{http_code}" "$BASE/objects/movies/sample.mp4"
```

Expected: `401`
