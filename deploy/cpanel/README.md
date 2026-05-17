# Deploying Planet Python on cPanel

> **Quick start (SSH):** if you can run shell commands on your cPanel host,
> use the one-shot installer:
>
> ```bash
> git clone https://github.com/kader14/planet.git ~/planet
> bash ~/planet/deploy/cpanel/setup.sh
> ```
>
> It creates the virtualenv, patches `config.ini`, runs the first build and
> prints the exact cron line to paste into cPanel.
>
> **No SSH?** Follow the visual, click-by-click walkthrough in
> [`VISUAL_GUIDE.md`](VISUAL_GUIDE.md) (Arabic + screenshots-style diagrams).
>
> The rest of this document is the manual reference.

---

Planet Python is a **static-site generator**, not a long-running web app: it
reads `config/config.ini`, downloads the configured RSS/Atom feeds, and writes
the rendered `index.html`, `rss20.xml`, `atom.xml`, … into `output_dir`. So
on cPanel the recipe is:

1. Put the source code somewhere outside `public_html` (e.g. `~/planet/`).
2. Install the Python dependencies in a virtualenv.
3. Point `output_dir` at the docroot of the (sub)domain you want to serve.
4. Run `code/planet.py` periodically via a Cron job.
5. Apache (the default web server in cPanel) serves the generated files
   directly — no Passenger / WSGI app needed.

The files in this directory are the glue: a templated `config.ini`, a cron
shell wrapper, and an optional `.htaccess`.

---

## 1. Upload the project

Use SSH (preferred) or cPanel's "File Manager" / Git Version Control to drop
the repository at `/home/<user>/planet/`:

```bash
ssh <user>@<host>
cd ~
git clone https://github.com/kader14/planet.git
```

The result should look like:

```
/home/<user>/planet/
├── code/
├── config/
├── deploy/cpanel/      <-- you are here
├── static/
└── requirements.txt
```

## 2. Create the Python environment

In cPanel: **Setup Python App** → *Create Application*

| Field                   | Value                                  |
| ----------------------- | -------------------------------------- |
| Python version          | 3.9 or newer (3.11 recommended)        |
| Application root        | `planet`                               |
| Application URL         | leave blank (we are not serving WSGI)  |
| Application startup file| leave blank                            |

Click **Create**, then on the same page:

* Use the *"Run Pip Install"* button against `requirements.txt`, **or** open
  the SSH shell and run:

  ```bash
  source ~/virtualenv/planet/3.11/bin/activate   # path shown by cPanel
  pip install -r ~/planet/requirements.txt
  ```

If your host does not expose "Setup Python App", create the venv by hand:

```bash
python3 -m venv ~/virtualenv/planet/3.11
source ~/virtualenv/planet/3.11/bin/activate
pip install -r ~/planet/requirements.txt
```

## 3. Configure paths

```bash
cp ~/planet/deploy/cpanel/config.ini.example ~/planet/config/local.ini
$EDITOR ~/planet/config/local.ini      # set output_dir / cache_directory
mkdir -p ~/planet/cache ~/planet/logs
```

Append the full feed list (every `[http...]` section) from
`~/planet/config/config.ini` to `local.ini`, **or** simply edit the original
`config/config.ini` and replace just its `[Planet]` block — both work.

> **Tip:** `output_dir` must be the docroot of a domain configured in cPanel.
> For the primary domain that's `~/public_html`. For a subdomain like
> `planet.example.com` use whatever path "Subdomains" reports.

## 4. Schedule the cron job

```bash
chmod +x ~/planet/deploy/cpanel/run-planet.sh
```

In cPanel → **Cron Jobs**, add:

```
*/30 * * * * /home/<user>/planet/deploy/cpanel/run-planet.sh
```

Every 30 minutes the script will:

* activate the virtualenv,
* run `python3 code/planet.py config/config.ini`,
* `rsync` the bundled `static/styles` and `static/images` into `output_dir`,
* append a timestamped line to `~/planet/logs/planet.log`.

For the very first run, execute it once manually to confirm everything works:

```bash
~/planet/deploy/cpanel/run-planet.sh
tail -n 50 ~/planet/logs/planet.log
ls -la ~/public_html/   # index.html, rss20.xml, etc. should now exist
```

## 5. (Optional) `.htaccess`

Copy `deploy/cpanel/.htaccess` into the same directory as the generated
output. It enables gzip, sane caching and HTTPS redirection. The site works
fine without it.

```bash
cp ~/planet/deploy/cpanel/.htaccess ~/public_html/.htaccess
```

## 6. Updating the code

```bash
cd ~/planet
git pull
source ~/virtualenv/planet/3.11/bin/activate
pip install -r requirements.txt   # in case dependencies changed
```

The next cron tick will pick up the new code.

---

## Troubleshooting

| Symptom                                              | Likely cause                                           |
| ---------------------------------------------------- | ------------------------------------------------------ |
| `ModuleNotFoundError: feedparser`                    | virtualenv not activated, or `pip install` was skipped |
| `Configuration missing [Planet] section`             | `config.ini` was edited incorrectly                    |
| HTML renders but stylesheets / logo are 404          | `static/` was not synced — re-run `run-planet.sh`      |
| Cron silently does nothing                           | `chmod +x run-planet.sh` was forgotten                 |
| Permission denied writing into `public_html`        | wrong `output_dir`, or directory owned by another user |

Always check `~/planet/logs/planet.log` first — every run appends to it.
