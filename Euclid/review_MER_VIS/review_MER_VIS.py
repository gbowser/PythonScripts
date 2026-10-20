"""Local, read-only FITS exploration and saved geometry reviews. No refitting."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import webbrowser

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u

APP_ID = "MER_VIS_sample_review_v1"
HERE = Path(__file__).resolve().parent
DEFAULT_DATA = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid")
CATEGORIES = {
    "sparse": "Sparse disc sampling",
    "bar": "Small candidate bar and boundary cases",
    "ellipticity": "Changing disc ellipticity and boundary cases",
    "variation": "Well-sampled disc PA variation",
    "control": "No counted geometry flags",
}
DEFAULT_RULES = dict(min_disc=6, max_gap=.5, pa_rms=10., eps_span=.15, small_bar=1.5)


def number(value, default=None):
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (ValueError, TypeError):
        return default


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def atomic_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(clean(value), indent=2, allow_nan=False), encoding="utf-8")
    for attempt in range(6):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(.15 * (attempt + 1))


def select_sample(rows):
    """48 unique, reproducible examples, including comparisons around thresholds."""
    fitted = [r for r in rows if r["codex_fit_status"] == "provisional_fit"]
    chosen, used = [], set()

    def flags(r):
        return set(filter(None, r["codex_quality_flags"].split(";")))

    def add(category, pool, count, reason, required=None):
        pool = [r for r in pool if r["object_id"] not in used]
        # Prefer isolated issues and complete requested cutouts within each stratum.
        pool.sort(key=lambda r: (str(r.get("cutout_partial")).lower() == "true",
                                 len(flags(r)), hashlib.sha256(r["object_id"].encode()).hexdigest()))
        if required:
            pool.sort(key=lambda r: r["object_id"] != required)
        for r in pool[:count]:
            used.add(r["object_id"])
            chosen.append(dict(object_id=r["object_id"], category=category,
                               category_label=CATEGORIES[category], selection_reason=reason))

    sparse = [r for r in fitted if "disc_PA_sparse_sampling" in flags(r)]
    add("sparse", [r for r in sparse if number(r.get("codex_n_disc"), 0) <= 3], 4,
        "Three or fewer accepted disc ellipses", "-518633776290631360")
    add("sparse", [r for r in sparse if 4 <= number(r.get("codex_n_disc"), 0) <= 5], 4,
        "Four or five accepted disc ellipses")
    add("sparse", [r for r in sparse if number(r.get("codex_n_disc"), 0) >= 6], 4,
        "Six or more points, but uneven radial coverage")
    add("sparse", sparse, 12 - sum(c["category"] == "sparse" for c in chosen),
        "Additional sparse sampling example")
    bars = [r for r in fitted if r.get("codex_bar_status", "").startswith("detected_")]
    for low, high, n, text in [(0, 1, 4, "Candidate bar end below 1 arcsec"),
                               (1, 1.5, 4, "Candidate bar end between 1 and 1.5 arcsec"),
                               (1.5, 2.2, 4, "Comparison just above the 1.5 arcsec warning")]:
        add("bar", [r for r in bars if low <= number(r.get("codex_bar_max_arcsec"), -1) < high], n, text)
    add("bar", bars, 12 - sum(c["category"] == "bar" for c in chosen), "Additional candidate bar")
    for low, high, text in [(.08, .15, "Ellipticity range just below the 0.15 threshold"),
                            (.15, .25, "Moderate ellipticity change above threshold"),
                            (.25, 1.1, "Pronounced ellipticity change")]:
        add("ellipticity", [r for r in fitted if low <= number(r.get("codex_disc_eps_span"), -1) < high], 4, text)
    add("variation", [r for r in fitted if "disc_PA_unstable" in flags(r)], 6,
        "Adequate sampling and disc PA scatter above 10 degrees", "-601121275504424227")
    add("control", [r for r in fitted if not flags(r) and str(r.get("cutout_partial")).lower() != "true"], 6,
        "No counted geometry flags; physical interpretation still needs checking")
    assert len(chosen) == len(used) == 48, f"Expected 48 unique examples, got {len(chosen)}"
    return chosen


class Store:
    def __init__(self, data_root, output):
        self.data_root, self.output = data_root, output
        output.mkdir(parents=True, exist_ok=True)
        self.manifest = data_root / "Euclid_MER_VIS_geometry/MER_VIS_local_geometry_manifest.csv"
        with self.manifest.open(encoding="utf-8-sig") as stream:
            self.rows = list(csv.DictReader(stream))
        self.byid = {r["object_id"]: r for r in self.rows}
        self.digest = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        sample_path = output / "MER_VIS_review_sample.json"
        if sample_path.exists():
            self.sample_document = json.loads(sample_path.read_text(encoding="utf-8"))
            self.sample = self.sample_document["sample"]
            if any(r["object_id"] not in self.byid for r in self.sample):
                raise ValueError("The saved sample references missing galaxies")
        else:
            self.sample = select_sample(self.rows)
            self.sample_document = dict(app=APP_ID, source_sha256=self.digest, sample=self.sample,
                                        selection="48 purposively stratified examples; not a population prevalence sample")
            atomic_json(sample_path, self.sample_document)
            with (output / "MER_VIS_review_sample.csv").open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=list(self.sample[0]))
                writer.writeheader()
                writer.writerows(self.sample)
        self.review_path = output / "MER_VIS_saved_reviews.json"
        self.reviews = json.loads(self.review_path.read_text(encoding="utf-8")) if self.review_path.exists() else {}
        self.lock = threading.RLock()
        self.profile_cache = {}

    def catalogue(self):
        return [dict(object_id=r["object_id"], name=r.get("catalogue_name", ""),
                     flags=r["codex_quality_flags"], status=r["codex_fit_status"]) for r in self.rows]

    def galaxy(self, oid):
        if oid not in self.byid:
            raise KeyError("Galaxy ID not in manifest")
        row = self.byid[oid]
        path = self.data_root / "Euclid_MER_VIS_geometry/profiles" / f"Euclid_{oid}_MER_VIS_ellipse_profile.csv"
        if oid not in self.profile_cache:
            profile = []
            if path.exists():
                with path.open(encoding="utf-8-sig") as stream:
                    profile = list(csv.DictReader(stream))
            converted = []
            for r in profile:
                p = {k: number(v) for k, v in r.items()}
                for k in ["valid", "used_for_geometry", "selected_disc", "selected_bar"]:
                    p[k] = str(r.get(k, "")).lower() == "true"
                p["marginal"] = bool(
                    p.get("valid") and p.get("stop_code") in (0, 2)
                    and (p.get("sampled_fraction") or 0) >= .5
                    and p.get("ellipticity_error") is not None and p["ellipticity_error"] < .2
                    and p.get("pa_error_deg") is not None and p["pa_error_deg"] < 20
                    and (p.get("intensity") or 0) > 0
                    and p.get("centre_offset_fit_pix") is not None
                    and p["centre_offset_fit_pix"] <= max(4, .25 * (p.get("sma_fit_pix") or 0)))
                converted.append(p)
            self.profile_cache[oid] = converted
        with fits.open(row["fits_path"], memmap=True) as hd:
            hdu = next(h for h in hd if h.header.get("NAXIS") == 2)
            header = hdu.header
            shape = (header["NAXIS2"], header["NAXIS1"])
            w = WCS(header).celestial
            scale = float(np.sqrt(abs(np.linalg.det(w.pixel_scale_matrix))) * 3600)
            cat = [number(row.get("codex_catalogue_centre_x_pix"), number(header.get("CENX"), shape[1]/2+1)-1),
                   number(row.get("codex_catalogue_centre_y_pix"), number(header.get("CENY"), shape[0]/2+1)-1)]
            centre = [number(row.get("codex_fit_centre_x_pix")), number(row.get("codex_fit_centre_y_pix"))]
            display_centre = centre if all(v is not None for v in centre) else cat
            sky = w.pixel_to_world(*display_centre)
            compass = {}
            for angle, label in [(0, "N"), (90, "E")]:
                px, py = w.world_to_pixel(sky.directional_offset_by(angle*u.deg, 1*u.arcsec))
                vec = np.array([px-display_centre[0], py-display_centre[1]])
                compass[label] = (vec/np.linalg.norm(vec)).tolist()
        profile = self.profile_cache[oid]
        outer = max([number(row.get("codex_disc_max_arcsec"), 0),
                     number(row.get("codex_bar_max_arcsec"), 0), 3])
        radius = max(outer * 1.45, 4) / scale
        x, y = display_centre
        window = [max(-.5, x-radius), min(shape[1]-.5, x+radius),
                  max(-.5, y-radius), min(shape[0]-.5, y+radius)]
        original = dict(disc_pa=number(row.get("codex_disc_pa_sky_deg")),
                        bar_pa=number(row.get("codex_bar_pa_sky_deg")),
                        inclination=number(row.get("codex_inclination_deg")),
                        n_disc=number(row.get("codex_n_disc")),
                        pa_scatter=number(row.get("codex_disc_pa_scatter_deg")),
                        eps_span=number(row.get("codex_disc_eps_span")),
                        flags=list(filter(None, row["codex_quality_flags"].split(";"))),
                        information=row.get("codex_information", ""),
                        bar_status=row.get("codex_bar_status", ""), status=row["codex_fit_status"])
        return clean(dict(object_id=oid, name=row.get("catalogue_name", ""), filename=Path(row["fits_path"]).name,
                          profile=profile, shape=shape, pixel_scale_arcsec=scale,
                          units=header.get("BUNIT", "FITS data units"), centre=centre, catalogue_centre=cat,
                          compass=compass, default_window=window, original=original,
                          intervals=dict(disc=[number(row.get("codex_disc_min_arcsec")), number(row.get("codex_disc_max_arcsec"))],
                                         bar=[number(row.get("codex_bar_min_arcsec")), number(row.get("codex_bar_max_arcsec"))]),
                          euclid=dict(disc_pa=number(row.get("euclid_adjusted_detection_pa_sky_deg")),
                                      inclination=number(row.get("euclid_detection_inclination_proxy_deg")),
                                      sersic_inclination=number(row.get("euclid_sersic_inclination_proxy_deg"))),
                          review=self.reviews.get(oid), fit_error=row.get("codex_error", "")))

    def image(self, oid, params):
        row = self.byid[oid]
        with fits.open(row["fits_path"], memmap=True) as hd:
            h = next(h for h in hd if h.header.get("NAXIS") == 2)
            ny, nx = h.header["NAXIS2"], h.header["NAXIS1"]
            def coord(key, default):
                v = number(params.get(key, [default])[0], default)
                return int(round(v + .5))
            x0, x1 = max(0, min(nx-1, coord("x0", -.5))), max(1, min(nx, coord("x1", nx-.5)))
            y0, y1 = max(0, min(ny-1, coord("y0", -.5))), max(1, min(ny, coord("y1", ny-.5)))
            if x1 <= x0 or y1 <= y0:
                raise ValueError("Empty image window")
            factor = max(1, math.ceil(max(x1-x0, y1-y0)/1200))
            x1, y1 = x0+max(1,(x1-x0)//factor)*factor, y0+max(1,(y1-y0)//factor)*factor
            if (x1-x0)*(y1-y0) <= 32_000_000:
                data = np.asarray(h.section[y0:y1, x0:x1], dtype=np.float32)
                if factor > 1:
                    data = np.nanmean(data.reshape(data.shape[0]//factor, factor, data.shape[1]//factor, factor), axis=(1,3))
                method = "native" if factor == 1 else "block mean preview"
            else:
                data = np.asarray(h.section[y0:y1:factor, x0:x1:factor], dtype=np.float32)
                method = "subsampled wide-field preview; zoom in for native pixels"
            finite = data[np.isfinite(data)]
            if not len(finite):
                raise ValueError("No finite pixels in this window")
            sample = finite[::max(1,len(finite)//100000)]
            median = float(np.median(sample)); mad = float(np.median(np.abs(sample-median)))
            noise = max(mad*1.4826, float(np.std(sample))*.001, 1e-15)
            stats = dict(median=median, noise=noise, percentiles=dict(zip(
                ["p1","p50","p95","p995","p999"], map(float,np.percentile(sample,[1,50,95,99.5,99.9])))))
            meta = dict(width=data.shape[1], height=data.shape[0], bounds=[x0-.5,x1-.5,y0-.5,y1-.5],
                        factor=factor, method=method, stats=stats)
            return clean(meta), np.ascontiguousarray(data, dtype="<f4").tobytes()

    def save(self, payload):
        oid = str(payload.get("object_id", ""))
        if oid not in self.byid:
            raise ValueError("Unknown galaxy")
        enums = {
            "disc_decision": ["not_assessed", "usable", "uncertain", "wrong_component"],
            "bar_decision": ["not_assessed", "convincing", "uncertain", "no_convincing_bar"],
            "centre_decision": ["not_assessed", "looks_correct", "uncertain", "off_centre"],
            "rule_action": ["unsure", "keep", "relax", "remove", "improve"],
        }
        for key, allowed in enums.items():
            if payload.get(key) not in allowed:
                raise ValueError(f"Invalid {key}")
        # Only explicit reviews are saved; exploring the display does not mark a galaxy reviewed.
        if all(payload[k] == "not_assessed" for k in ["disc_decision", "bar_decision", "centre_decision"]) and not str(payload.get("notes", "")).strip():
            raise ValueError("Add a decision or a note before saving")
        notes = str(payload.get("notes", ""))[:6000]
        settings = payload.get("settings", {})
        if not isinstance(settings, dict) or len(json.dumps(settings)) > 30000:
            raise ValueError("Invalid settings")
        record = {k: payload[k] for k in enums}
        record.update(object_id=oid, catalogue_name=self.byid[oid].get("catalogue_name", ""),
                      category=next((s["category"] for s in self.sample if s["object_id"] == oid), "extra"),
                      notes=notes, settings=settings, calculation=payload.get("calculation", {}),
                      reviewed_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                      source_manifest_sha256=self.digest,
                      original_disc_pa=number(self.byid[oid].get("codex_disc_pa_sky_deg")),
                      original_bar_pa=number(self.byid[oid].get("codex_bar_pa_sky_deg")),
                      original_inclination=number(self.byid[oid].get("codex_inclination_deg")))
        with self.lock:
            updated = dict(self.reviews); updated[oid] = clean(record)
            atomic_json(self.review_path, updated)
            self.reviews = updated
            # JSON is authoritative if Excel has locked the convenience CSV.
            warning = None
            try:
                (self.output / "MER_VIS_saved_reviews.csv").write_bytes(self.export_csv())
            except PermissionError:
                warning = "Review saved in JSON. Close the CSV in Excel to refresh the CSV copy."
        return dict(saved=True, review=record, reviewed=len(self.reviews), warning=warning)

    def export_csv(self):
        fields = ["object_id","catalogue_name","category","disc_decision","bar_decision","centre_decision",
                  "rule_action","notes","reviewed_utc","original_disc_pa","original_bar_pa","original_inclination",
                  "trial_disc_pa","trial_bar_pa","trial_inclination","trial_disc_samples","trial_disc_scatter",
                  "trial_disc_eps_span","settings_json","source_manifest_sha256"]
        stream = io.StringIO(newline=""); writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        with self.lock:
            for r in self.reviews.values():
                result = {k:r.get(k,"") for k in fields}
                calc = r.get("calculation", {})
                for k, src in [("trial_disc_pa","disc_pa"),("trial_bar_pa","bar_pa"),("trial_inclination","inclination"),
                               ("trial_disc_samples","n_disc"),("trial_disc_scatter","pa_scatter"),("trial_disc_eps_span","eps_span")]:
                    result[k] = calc.get(src, "")
                result["settings_json"] = json.dumps(r.get("settings", {}), ensure_ascii=False)
                writer.writerow(result)
        return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(time.strftime("%H:%M:%S"), format % args, flush=True)

    def send(self, body, kind="application/json; charset=utf-8", status=200, extra=None):
        if isinstance(body, (dict,list)):
            body = json.dumps(clean(body),allow_nan=False).encode("utf-8")
        elif isinstance(body,str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if extra:
            for k,v in extra.items(): self.send_header(k,v)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        try:
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                return self.send(dict(error="Use the local 127.0.0.1 review URL"), status=403)
            parsed=urlparse(self.path); params=parse_qs(parsed.query); route=parsed.path
            if route == "/api/health":
                return self.send(dict(app=APP_ID))
            if route == "/api/bootstrap":
                return self.send(dict(app=APP_ID,token=self.server.token,sample=self.server.store.sample,
                    categories=CATEGORIES,rules=DEFAULT_RULES,reviews=self.server.store.reviews,
                    catalogue=self.server.store.catalogue(),output=str(self.server.store.output),
                    storage_key=hashlib.sha256(str(self.server.store.output.resolve()).encode()).hexdigest()[:16],
                    source_sha256=self.server.store.digest,
                    sample_source_changed=self.server.store.sample_document["source_sha256"] != self.server.store.digest))
            if route == "/api/galaxy":
                return self.send(self.server.store.galaxy(params.get("id",[""])[0]))
            if route == "/api/image":
                meta, data = self.server.store.image(params.get("id",[""])[0],params)
                return self.send(gzip.compress(data,compresslevel=1), "application/octet-stream", extra={
                    "Content-Encoding":"gzip","X-Image-Meta":json.dumps(meta,separators=(",",":"))})
            if route == "/api/export":
                return self.send(self.server.store.export_csv(),"text/csv; charset=utf-8",extra={
                    "Content-Disposition":'attachment; filename="MER_VIS_saved_reviews.csv"'})
            static = {"/":"index.html","/app.js":"app.js","/style.css":"style.css"}
            if route in static:
                filename=static[route]
                return self.send((HERE/filename).read_bytes(), {"index.html":"text/html; charset=utf-8",
                    "app.js":"text/javascript; charset=utf-8","style.css":"text/css; charset=utf-8"}[filename])
            self.send(dict(error="Not found"),status=404)
        except (KeyError,ValueError) as exc:
            self.send(dict(error=str(exc)),status=400)
        except (BrokenPipeError,ConnectionResetError):
            pass
        except Exception as exc:
            import traceback;traceback.print_exc()
            self.send(dict(error=str(exc)),status=500)

    def do_POST(self):
        try:
            origin = self.headers.get("Origin")
            allowed = f"http://127.0.0.1:{self.server.server_port}"
            if (self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}"
                    or self.headers.get("X-Review-Token") != self.server.token or (origin and origin != allowed)):
                return self.send(dict(error="Invalid local review request"),status=403)
            length=int(self.headers.get("Content-Length","0"))
            if length <= 0 or length > 100_000:
                return self.send(dict(error="Invalid request size"),status=400)
            payload=json.loads(self.rfile.read(length))
            if self.path == "/api/review": return self.send(self.server.store.save(payload))
            if self.path == "/api/stop":
                self.send(dict(stopped=True)); threading.Thread(target=self.server.shutdown,daemon=True).start(); return
            self.send(dict(error="Not found"),status=404)
        except (ValueError,KeyError) as exc:
            self.send(dict(error=str(exc)),status=400)
        except Exception as exc:
            self.send(dict(error=str(exc)),status=500)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",type=Path,default=DEFAULT_DATA)
    p.add_argument("--output",type=Path,default=HERE/"saved_reviews")
    p.add_argument("--port",type=int,default=8768)
    p.add_argument("--no-browser",action="store_true")
    p.add_argument("--prepare-only",action="store_true")
    a=p.parse_args(); store=Store(a.data_root,a.output)
    if a.prepare_only:
        print(json.dumps(dict(sample=len(store.sample),output=str(a.output))));return
    server=None
    for port in range(a.port,a.port+20):
        try: server=ThreadingHTTPServer(("127.0.0.1",port),Handler); break
        except OSError: continue
    if server is None:raise RuntimeError("No free local review port")
    server.store=store;server.token=secrets.token_urlsafe(32)
    url=f"http://127.0.0.1:{server.server_port}/"
    atomic_json(a.output/"server.json",dict(app=APP_ID,pid=os.getpid(),url=url))
    print(f"MER VIS review ready: {url}\nSaved reviews: {a.output}",flush=True)
    if not a.no_browser:threading.Timer(.6,lambda:webbrowser.open(url)).start()
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__ == "__main__":main()
