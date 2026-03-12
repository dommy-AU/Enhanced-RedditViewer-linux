from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import requests
from flask import Flask, Response, render_template_string, request, session, stream_with_context

APP_TITLE = "Reddit Public Media Viewer"
USER_AGENT = os.getenv(
    "REDDIT_VIEWER_USER_AGENT",
    "linuxmint:reddit-public-media-viewer:2.4 (by /u/local-user)",
)
REQUEST_TIMEOUT = 20
MAX_SUBREDDIT_RESULTS = 25
MAX_USER_RESULTS = 25

DISPLAY_MEDIA_ITEMS_PER_PAGE = 200
API_BATCH_SIZE = 100
MAX_API_PAGES_PER_VIEW = 10
MAX_API_PAGES_PER_SEARCH = 100

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m4v")
GIFV_EXTENSIONS = (".gifv",)

TOP_TIME_OPTIONS = [
    ("hour", "Now"),
    ("day", "Today"),
    ("week", "This week"),
    ("month", "This month"),
    ("year", "This year"),
    ("all", "All time"),
]

UI_SORT_OPTIONS = [
    ("best", "Best"),
    ("new", "New"),
    ("rising", "Rising"),
    ("top", "Top"),
    ("hot", "Hot"),
]

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-before-exposing-this")

PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #07101c;
      --bg-2: #0b1830;
      --panel: rgba(16, 25, 44, 0.84);
      --panel-2: rgba(20, 32, 58, 0.90);
      --panel-3: rgba(10, 18, 33, 0.94);
      --panel-4: rgba(19, 30, 53, 0.78);
      --text: #edf2ff;
      --muted: #afbddc;
      --muted-2: #8495ba;
      --border: rgba(104, 129, 183, 0.26);
      --border-strong: rgba(150, 183, 255, 0.34);
      --accent: #8ab7ff;
      --accent-2: #bb92ff;
      --accent-3: #94f2d9;
      --accent-4: #ffd4ef;
      --danger: #ff8f8f;
      --shadow: 0 24px 54px rgba(0, 0, 0, 0.36);
      --shadow-soft: 0 14px 30px rgba(0, 0, 0, 0.22);
      --radius: 24px;
      --radius-sm: 18px;
      --radius-pill: 999px;
      --max: 1450px;
    }

    * { box-sizing: border-box; }

    html { scroll-behavior: smooth; }

    body {
      margin: 0;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 8% 12%, rgba(148, 242, 217, 0.08), transparent 24%),
        radial-gradient(circle at 90% 10%, rgba(187, 146, 255, 0.14), transparent 24%),
        radial-gradient(circle at 50% -8%, rgba(138, 183, 255, 0.14), transparent 32%),
        linear-gradient(180deg, #040913 0%, var(--bg) 34%, var(--bg-2) 100%);
      min-height: 100vh;
    }

    body::before,
    body::after {
      content: "";
      position: fixed;
      pointer-events: none;
      z-index: 0;
      filter: blur(90px);
      opacity: 0.42;
      border-radius: 50%;
    }

    body::before {
      width: 380px;
      height: 380px;
      top: 78px;
      left: -95px;
      background: radial-gradient(circle, rgba(138, 183, 255, 0.24) 0%, transparent 72%);
    }

    body::after {
      width: 430px;
      height: 430px;
      top: 36px;
      right: -130px;
      background: radial-gradient(circle, rgba(187, 146, 255, 0.20) 0%, transparent 72%);
    }

    .wrap {
      position: relative;
      z-index: 1;
      width: min(var(--max), calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 44px;
    }

    h1 {
      margin: 0;
      font-size: clamp(2.45rem, 4.8vw, 4.5rem);
      line-height: 1.02;
      letter-spacing: -0.05em;
      font-weight: 900;
      text-wrap: balance;
    }

    h2 { margin: 0; }

    p {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }

    a { color: inherit; }

    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 22px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      margin-bottom: 18px;
      overflow: hidden;
    }

    .hero-card {
      position: relative;
      padding: 30px 24px 26px;
      background:
        linear-gradient(180deg, rgba(21, 33, 58, 0.96) 0%, rgba(10, 18, 33, 0.92) 100%);
      border: 1px solid rgba(136, 165, 220, 0.18);
    }

    .hero-card::before,
    .hero-card::after {
      content: "";
      position: absolute;
      border-radius: 50%;
      pointer-events: none;
      filter: blur(20px);
      opacity: 0.75;
    }

    .hero-card::before {
      width: 320px;
      height: 320px;
      top: -130px;
      left: -48px;
      background: radial-gradient(circle, rgba(138, 183, 255, 0.18) 0%, transparent 72%);
    }

    .hero-card::after {
      width: 360px;
      height: 360px;
      top: -120px;
      right: -66px;
      background: radial-gradient(circle, rgba(187, 146, 255, 0.18) 0%, transparent 72%);
    }

    .hero-banner {
      position: relative;
      text-align: center;
      padding: 8px 0 6px;
    }

    .hero-badge-image-wrap {
      display: flex;
      justify-content: center;
      align-items: center;
      margin-bottom: 18px;
    }

    .hero-badge-image {
      width: clamp(110px, 15vw, 165px);
      height: auto;
      display: block;
      border-radius: 28px;
      border: 1px solid rgba(255, 255, 255, 0.14);
      box-shadow:
        0 18px 42px rgba(0, 0, 0, 0.32),
        0 0 0 6px rgba(255, 255, 255, 0.03);
      background: rgba(255, 255, 255, 0.04);
    }

    .hero-title {
      display: inline-block;
      background: linear-gradient(135deg, #ffffff 0%, #deebff 36%, #b7d7ff 64%, #d4bdff 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      text-shadow: 0 0 22px rgba(138, 183, 255, 0.10);
    }

    .hero-flourish {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 16px;
      margin: 18px auto 18px;
      color: #d9e4ff;
      opacity: 0.96;
    }

    .hero-flourish::before,
    .hero-flourish::after {
      content: "";
      width: 120px;
      max-width: 18vw;
      height: 1px;
      background: linear-gradient(90deg, transparent 0%, rgba(173, 190, 224, 0.68) 50%, transparent 100%);
    }

    .hero-flourish span {
      font-size: 1.06rem;
      letter-spacing: 0.22em;
      color: var(--accent-3);
      text-shadow: 0 0 14px rgba(148, 242, 217, 0.18);
    }

    .hero-copy {
      max-width: 980px;
      margin: 0 auto;
      text-align: center;
      font-size: 1.02rem;
      color: #cad7f2;
      text-wrap: balance;
    }

    .hero-copy strong {
      color: #eef5ff;
      font-weight: 700;
    }

    .control-panel {
      margin-top: 28px;
      padding: 26px 24px 24px;
      border: 1px solid rgba(132, 160, 213, 0.18);
      border-radius: 28px;
      background:
        linear-gradient(180deg, rgba(24, 38, 67, 0.86) 0%, rgba(10, 18, 33, 0.92) 100%);
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.04),
        0 20px 38px rgba(0,0,0,0.18);
      position: relative;
      overflow: hidden;
    }

    .control-panel::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(120deg, transparent 0%, rgba(255,255,255,0.024) 28%, transparent 55%);
      opacity: 0.9;
    }

    .control-panel::after {
      content: "❦   ✦   ❦   ✦   ❦   ✦   ❦";
      position: absolute;
      left: 50%;
      top: 10px;
      transform: translateX(-50%);
      font-size: 0.94rem;
      letter-spacing: 0.7rem;
      color: rgba(148, 242, 217, 0.18);
      white-space: nowrap;
      pointer-events: none;
      text-shadow: 0 0 18px rgba(148, 242, 217, 0.10);
    }

    .menu-ornament-top,
    .menu-ornament-bottom {
      position: relative;
      z-index: 1;
      text-align: center;
      font-size: 0.98rem;
      letter-spacing: 0.55rem;
      color: rgba(187, 146, 255, 0.34);
      text-shadow: 0 0 18px rgba(187, 146, 255, 0.12);
      user-select: none;
      pointer-events: none;
    }

    .menu-ornament-top {
      margin: 0 0 18px;
    }

    .menu-ornament-bottom {
      margin: 16px 0 0;
      color: rgba(148, 242, 217, 0.24);
    }

    .search-grid {
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 18px;
      align-items: stretch;
    }

    .search-grid-secondary {
      position: relative;
      z-index: 1;
      display: flex;
      justify-content: center;
      align-items: stretch;
      gap: 18px;
      margin-top: 18px;
      flex-wrap: wrap;
    }

    .field-group {
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: 9px;
      min-width: 0;
      min-height: 122px;
      padding: 18px 18px 18px;
      border-radius: 22px;
      border: 1px solid rgba(120, 145, 197, 0.18);
      background:
        radial-gradient(circle at 12% 18%, rgba(148, 242, 217, 0.08), transparent 28%),
        radial-gradient(circle at 88% 18%, rgba(187, 146, 255, 0.10), transparent 28%),
        linear-gradient(180deg, rgba(25, 39, 67, 0.60) 0%, rgba(9, 16, 30, 0.42) 100%);
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.03),
        0 10px 18px rgba(0,0,0,0.12);
      overflow: hidden;
      transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    }

    .field-group:hover {
      transform: translateY(-2px);
      border-color: rgba(147, 177, 236, 0.28);
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.04),
        0 14px 22px rgba(0,0,0,0.16);
    }

    .field-group::before {
      content: "❦";
      position: absolute;
      top: 12px;
      left: 14px;
      font-size: 0.95rem;
      color: rgba(148, 242, 217, 0.62);
      text-shadow: 0 0 10px rgba(148, 242, 217, 0.14);
      pointer-events: none;
    }

    .field-group::after {
      content: "❦";
      position: absolute;
      top: 12px;
      right: 14px;
      font-size: 0.95rem;
      color: rgba(187, 146, 255, 0.58);
      text-shadow: 0 0 10px rgba(187, 146, 255, 0.14);
      pointer-events: none;
    }

    .field-group .field-footer-line {
      position: absolute;
      left: 16px;
      right: 16px;
      bottom: 12px;
      height: 1px;
      background: linear-gradient(90deg, transparent 0%, rgba(187, 146, 255, 0.16) 20%, rgba(148, 242, 217, 0.30) 50%, rgba(187, 146, 255, 0.16) 80%, transparent 100%);
      pointer-events: none;
    }

    .field-group.compact {
      width: min(280px, 100%);
      min-height: 118px;
    }

    .field-label {
      position: relative;
      z-index: 1;
      text-align: center;
      font-size: 0.76rem;
      font-weight: 800;
      letter-spacing: 0.13em;
      text-transform: uppercase;
      color: #ccdaf7;
      padding: 0 8px;
    }

    .field-label::before,
    .field-label::after {
      content: "✦";
      color: rgba(148, 242, 217, 0.76);
      font-size: 0.72rem;
      margin: 0 0.45rem;
    }

    input[type="text"], select {
      position: relative;
      z-index: 1;
      width: 100%;
      min-height: 56px;
      padding: 14px 16px;
      border-radius: var(--radius-sm);
      border: 1px solid rgba(112, 136, 184, 0.30);
      background: rgba(7, 13, 24, 0.84);
      color: var(--text);
      outline: none;
      font-size: 0.98rem;
      text-align: center;
      transition:
        border-color 0.18s ease,
        box-shadow 0.18s ease,
        transform 0.18s ease,
        background 0.18s ease;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
    }

    input[type="text"]::placeholder {
      color: var(--muted-2);
      text-align: center;
    }

    input[type="text"]:focus,
    select:focus {
      border-color: rgba(138, 183, 255, 0.84);
      box-shadow: 0 0 0 4px rgba(138, 183, 255, 0.14);
      background: rgba(10, 17, 31, 0.96);
      transform: translateY(-1px);
    }

    .field-highlight {
      border-color: rgba(148, 242, 217, 0.92) !important;
      box-shadow: 0 0 0 4px rgba(148, 242, 217, 0.16) !important;
      background: rgba(10, 19, 31, 0.98) !important;
    }

    .actions-row {
      position: relative;
      z-index: 1;
      margin-top: 20px;
      padding-top: 18px;
      border-top: 1px solid rgba(92, 118, 170, 0.34);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .actions-left,
    .actions-right {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px;
    }

    button, .button-link {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      border: 0;
      border-radius: var(--radius-sm);
      padding: 13px 18px;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 55%, #b9f6e8 120%);
      color: #06101c;
      font-weight: 900;
      cursor: pointer;
      text-decoration: none;
      min-height: 50px;
      box-shadow: 0 10px 22px rgba(0, 0, 0, 0.22);
      transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
    }

    button:hover,
    .button-link:hover {
      transform: translateY(-1px);
      box-shadow: 0 16px 30px rgba(0, 0, 0, 0.28);
    }

    .button-link.muted {
      background: rgba(31, 49, 84, 0.92);
      color: var(--text);
      border: 1px solid rgba(99, 123, 174, 0.26);
      box-shadow: none;
    }

    .checkbox {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      min-height: 50px;
      padding: 0 2px;
      font-size: 0.95rem;
      color: var(--muted);
    }

    .checkbox input[type="checkbox"] {
      width: 18px;
      height: 18px;
      accent-color: #8aaeff;
      flex: 0 0 auto;
    }

    .nsfw-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 50px;
      padding: 0 16px;
      border-radius: 999px;
      position: relative;
      color: #ffd3ea;
      font-weight: 900;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      font-size: 0.82rem;
      background:
        linear-gradient(180deg, rgba(76, 17, 44, 0.78) 0%, rgba(45, 10, 30, 0.84) 100%);
      border: 1px solid rgba(255, 155, 206, 0.30);
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.06),
        0 8px 18px rgba(0, 0, 0, 0.18);
    }

    .nsfw-badge::before,
    .nsfw-badge::after {
      content: "❦";
      color: #ffb8da;
      font-size: 0.9rem;
      text-shadow: 0 0 12px rgba(255, 155, 206, 0.18);
    }

    .results-showcase {
      position: relative;
      margin-top: 22px;
      padding-top: 8px;
    }

    .results-showcase::before {
      content: "❦ ✦ ❦";
      display: block;
      text-align: center;
      color: rgba(148, 242, 217, 0.30);
      letter-spacing: 0.45rem;
      font-size: 0.94rem;
      margin-bottom: 10px;
      text-shadow: 0 0 16px rgba(148, 242, 217, 0.10);
    }

    .split {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-top: 14px;
    }

    .results-panel {
      position: relative;
      padding: 20px 18px 18px;
      border-radius: 24px;
      border: 1px solid rgba(124, 149, 202, 0.20);
      background:
        radial-gradient(circle at 12% 10%, rgba(148, 242, 217, 0.08), transparent 28%),
        radial-gradient(circle at 88% 10%, rgba(255, 212, 239, 0.08), transparent 24%),
        linear-gradient(180deg, rgba(23, 36, 62, 0.74) 0%, rgba(10, 17, 31, 0.58) 100%);
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.03),
        0 16px 30px rgba(0,0,0,0.18);
      overflow: hidden;
    }

    .results-panel::before {
      content: "❦";
      position: absolute;
      top: 14px;
      left: 16px;
      font-size: 1rem;
      color: rgba(148, 242, 217, 0.60);
      text-shadow: 0 0 12px rgba(148, 242, 217, 0.14);
    }

    .results-panel::after {
      content: "❦";
      position: absolute;
      top: 14px;
      right: 16px;
      font-size: 1rem;
      color: rgba(255, 212, 239, 0.58);
      text-shadow: 0 0 12px rgba(255, 212, 239, 0.14);
    }

    .section-title {
      text-align: center;
      font-size: 1.06rem;
      margin: 0 0 12px;
      color: #edf4ff;
      letter-spacing: 0.02em;
      position: relative;
      z-index: 1;
    }

    .section-title span {
      display: inline-flex;
      align-items: center;
      gap: 0.6rem;
    }

    .section-title span::before,
    .section-title span::after {
      content: "✦";
      color: rgba(148, 242, 217, 0.78);
      font-size: 0.78rem;
    }

    .results-divider {
      position: relative;
      z-index: 1;
      height: 1px;
      margin: 0 auto 14px;
      width: min(260px, 72%);
      background: linear-gradient(90deg, transparent 0%, rgba(187, 146, 255, 0.20) 20%, rgba(148, 242, 217, 0.34) 50%, rgba(187, 146, 255, 0.20) 80%, transparent 100%);
    }

    .results-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      margin-top: 6px;
      position: relative;
      z-index: 1;
    }

    .result-card {
      position: relative;
      padding: 16px 16px 18px;
      border-radius: 20px;
      border: 1px solid rgba(109, 133, 184, 0.24);
      background:
        radial-gradient(circle at 12% 16%, rgba(148, 242, 217, 0.07), transparent 24%),
        radial-gradient(circle at 88% 16%, rgba(255, 212, 239, 0.08), transparent 22%),
        linear-gradient(180deg, rgba(15, 24, 43, 0.94) 0%, rgba(9, 15, 28, 0.90) 100%);
      text-decoration: none;
      color: var(--text);
      transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.03),
        0 10px 20px rgba(0,0,0,0.18);
      overflow: hidden;
    }

    .result-card:hover {
      transform: translateY(-3px);
      border-color: rgba(153, 184, 243, 0.36);
      background:
        radial-gradient(circle at 12% 16%, rgba(148, 242, 217, 0.10), transparent 24%),
        radial-gradient(circle at 88% 16%, rgba(255, 212, 239, 0.10), transparent 22%),
        linear-gradient(180deg, rgba(17, 27, 48, 0.98) 0%, rgba(10, 17, 31, 0.96) 100%);
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.04),
        0 14px 24px rgba(0,0,0,0.22);
    }

    .result-card::before {
      content: "❦";
      position: absolute;
      top: 12px;
      left: 12px;
      font-size: 0.88rem;
      color: rgba(148, 242, 217, 0.52);
      text-shadow: 0 0 8px rgba(148, 242, 217, 0.12);
    }

    .result-card::after {
      content: "❦";
      position: absolute;
      top: 12px;
      right: 12px;
      font-size: 0.88rem;
      color: rgba(255, 212, 239, 0.52);
      text-shadow: 0 0 8px rgba(255, 212, 239, 0.12);
    }

    .result-title {
      display: block;
      text-align: center;
      font-weight: 800;
      font-size: 1rem;
      color: #eff5ff;
      padding: 8px 22px 0;
    }

    .result-line {
      height: 1px;
      margin: 12px auto 10px;
      width: min(160px, 72%);
      background: linear-gradient(90deg, transparent 0%, rgba(187, 146, 255, 0.18) 25%, rgba(148, 242, 217, 0.34) 50%, rgba(187, 146, 255, 0.18) 75%, transparent 100%);
    }

    .result-card small {
      color: var(--muted);
      display: block;
      margin-top: 4px;
      line-height: 1.45;
      text-align: center;
    }

    .toolbar-card {
      position: relative;
      background:
        radial-gradient(circle at 10% 12%, rgba(148, 242, 217, 0.07), transparent 22%),
        radial-gradient(circle at 90% 12%, rgba(255, 212, 239, 0.08), transparent 22%),
        linear-gradient(180deg, rgba(20, 32, 58, 0.88) 0%, rgba(10, 18, 33, 0.92) 100%);
      border: 1px solid rgba(128, 154, 207, 0.18);
    }

    .toolbar-card::before {
      content: "❦   ✦   ❦";
      position: absolute;
      left: 50%;
      top: 10px;
      transform: translateX(-50%);
      color: rgba(148, 242, 217, 0.24);
      letter-spacing: 0.45rem;
      font-size: 0.88rem;
      pointer-events: none;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      position: relative;
      z-index: 1;
      margin-top: 6px;
    }

    .toolbar-left {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }

    .notice, .error {
      border-radius: var(--radius-sm);
      padding: 14px 16px;
      margin: 14px 0;
      border: 1px solid var(--border);
    }

    .notice {
      background: rgba(28, 44, 74, 0.8);
      color: #dbe8ff;
    }

    .error {
      background: rgba(98, 31, 31, 0.5);
      color: #ffd6d6;
      border-color: rgba(255, 122, 122, 0.4);
    }

    .gallery {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
      margin-top: 18px;
    }

    .tile {
      display: block;
      overflow: hidden;
      border-radius: 20px;
      border: 1px solid rgba(104, 129, 183, 0.22);
      background:
        linear-gradient(180deg, rgba(13, 20, 36, 0.98) 0%, rgba(10, 16, 28, 0.98) 100%);
      text-decoration: none;
      color: var(--text);
      box-shadow: 0 12px 24px rgba(0,0,0,0.20);
      position: relative;
    }

    .tile::before {
      content: "❦";
      position: absolute;
      top: 10px;
      left: 12px;
      z-index: 4;
      font-size: 0.86rem;
      color: rgba(148, 242, 217, 0.55);
      text-shadow: 0 0 8px rgba(148, 242, 217, 0.12);
      pointer-events: none;
    }

    .tile::after {
      content: "❦";
      position: absolute;
      top: 10px;
      right: 12px;
      z-index: 4;
      font-size: 0.86rem;
      color: rgba(255, 212, 239, 0.52);
      text-shadow: 0 0 8px rgba(255, 212, 239, 0.12);
      pointer-events: none;
    }

    .media-shell {
      position: relative;
      width: 100%;
      background: #060a13;
    }

    .media-frame {
      width: 100%;
      height: 320px;
      display: block;
      background: #060a13;
      object-fit: cover;
    }

    .tile video.media-frame {
      background: #000;
    }

    .media-pill {
      position: absolute;
      top: 12px;
      left: 36px;
      z-index: 3;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(5, 9, 20, 0.72);
      border: 1px solid rgba(255,255,255,0.12);
      color: var(--text);
      font-size: 0.75rem;
      font-weight: 700;
      backdrop-filter: blur(6px);
    }

    .media-load-btn {
      position: absolute;
      left: 50%;
      bottom: 16px;
      transform: translateX(-50%);
      z-index: 3;
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      min-height: 0;
      background: rgba(8, 14, 26, 0.9);
      color: var(--text);
      font-weight: 700;
      border: 1px solid rgba(255,255,255,0.12);
      box-shadow: 0 8px 18px rgba(0,0,0,0.25);
      cursor: pointer;
    }

    .media-carousel {
      position: relative;
    }

    .media-slide {
      display: none;
    }

    .media-slide.is-active {
      display: block;
    }

    .media-count-badge {
      position: absolute;
      top: 12px;
      right: 36px;
      z-index: 3;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(5, 9, 20, 0.72);
      border: 1px solid rgba(255,255,255,0.12);
      color: var(--text);
      font-size: 0.75rem;
      font-weight: 700;
      backdrop-filter: blur(6px);
    }

    .media-carousel-nav {
      position: absolute;
      left: 12px;
      right: 12px;
      bottom: 12px;
      z-index: 3;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      pointer-events: none;
    }

    .media-nav-button,
    .media-nav-status {
      pointer-events: auto;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(8, 14, 26, 0.9);
      color: var(--text);
      box-shadow: 0 8px 18px rgba(0,0,0,0.25);
      backdrop-filter: blur(6px);
    }

    .media-nav-button {
      min-width: 42px;
      min-height: 42px;
      padding: 0 14px;
      font-size: 1.2rem;
      line-height: 1;
      font-weight: 800;
      cursor: pointer;
    }

    .media-nav-status {
      padding: 8px 12px;
      font-size: 0.8rem;
      font-weight: 700;
      text-align: center;
    }

    .media-shell.is-loaded .media-load-btn {
      opacity: 0;
      pointer-events: none;
    }

    .tile-body {
      padding: 14px 14px 16px;
      position: relative;
    }

    .tile-body::before {
      content: "";
      display: block;
      height: 1px;
      width: min(160px, 72%);
      margin: 0 auto 12px;
      background: linear-gradient(90deg, transparent 0%, rgba(187, 146, 255, 0.18) 25%, rgba(148, 242, 217, 0.34) 50%, rgba(187, 146, 255, 0.18) 75%, transparent 100%);
    }

    .title {
      font-size: 0.94rem;
      line-height: 1.38;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      min-height: 2.6em;
      text-align: center;
    }

    .meta {
      color: var(--muted);
      font-size: 0.81rem;
      margin-top: 8px;
      text-align: center;
    }

    .tile-actions {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 10px;
      margin-top: 14px;
    }


    .pagination-footer {
      display: flex;
      justify-content: center;
      margin-top: 22px;
    }

    .results-search {
      display: inline-flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      min-width: min(100%, 430px);
      padding: 6px 8px;
      border-radius: 999px;
      border: 1px solid rgba(128, 154, 207, 0.18);
      background: rgba(10, 16, 28, 0.72);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }

    .results-search-input {
      width: min(100%, 240px);
      border: 0;
      outline: none;
      background: transparent;
      color: var(--text);
      font: inherit;
    }

    .results-search-input::placeholder {
      color: rgba(198, 214, 244, 0.48);
    }

    .results-search-button,
    .results-search-clear {
      border: 0;
      background: rgba(148, 242, 217, 0.1);
      color: #dffdf6;
      border-radius: 999px;
      padding: 6px 10px;
      font: inherit;
      font-size: 0.9rem;
      cursor: pointer;
      transition: background 0.18s ease, transform 0.18s ease;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      white-space: nowrap;
    }

    .results-search-button {
      background: rgba(138, 183, 255, 0.16);
      color: #edf5ff;
    }

    .results-search-button:hover,
    .results-search-clear:hover {
      background: rgba(148, 242, 217, 0.18);
      transform: translateY(-1px);
    }

    .results-search-button:hover {
      background: rgba(138, 183, 255, 0.24);
    }

    .results-search-meta {
      margin-top: 14px;
    }

    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }

    .tile-action-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 42px;
      padding: 10px 14px;
      border-radius: 999px;
      border: 0;
      text-decoration: none;
      cursor: pointer;
      font-weight: 800;
      font-size: 0.88rem;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 55%, #b9f6e8 120%);
      color: #06101c;
      box-shadow: 0 8px 18px rgba(0, 0, 0, 0.18);
      transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
    }

    .tile-action-button:hover {
      transform: translateY(-1px);
      box-shadow: 0 12px 22px rgba(0, 0, 0, 0.24);
    }

    .tile-action-button.secondary {
      background: rgba(31, 49, 84, 0.92);
      color: var(--text);
      border: 1px solid rgba(99, 123, 174, 0.26);
      box-shadow: none;
    }

    .muted-line {
      color: var(--muted);
      font-size: 0.95rem;
      margin-top: 12px;
      position: relative;
      z-index: 1;
    }

    .is-hidden {
      display: none !important;
    }

    @media (max-width: 1180px) {
      .search-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 980px) {
      .split { grid-template-columns: 1fr; }
      .toolbar { align-items: flex-start; }
      .media-frame { height: 260px; }
    }

    @media (max-width: 760px) {
      .search-grid {
        grid-template-columns: 1fr;
      }

      .search-grid-secondary {
        flex-direction: column;
        align-items: stretch;
      }

      .field-group.compact {
        width: 100%;
      }

      .actions-row {
        flex-direction: column;
        align-items: stretch;
      }

      .actions-left,
      .actions-right {
        width: 100%;
        justify-content: stretch;
      }

      .actions-left > *,
      .actions-right > * {
        width: 100%;
      }

      .wrap {
        width: min(100%, calc(100% - 20px));
      }

      .hero-flourish::before,
      .hero-flourish::after {
        width: 58px;
      }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card hero-card">
      <div class="hero-banner">
        <div class="hero-badge-image-wrap">
          <img
            class="hero-badge-image"
            src="{{ url_for('static', filename='Icon.png') }}"
            alt="Reddit Viewer icon"
          >
        </div>
        <h1><span class="hero-title">{{ title }}</span></h1>
        <div class="hero-flourish"><span>❦ ✦ ❦</span></div>
        <p class="hero-copy">
          Search for <strong>subreddits</strong> or <strong>users</strong>, then open a beautifully arranged media-only gallery.
          This local app shows public Reddit media that guest access allows, keeps comments out of the way and loads videos and GIF-style clips on demand for a smoother experience.
          It will try to display up to <strong>100 unique media items per page</strong>.
        </p>
      </div>

      <div class="control-panel">
        <div class="menu-ornament-top">❦ ✦ ❦ ✦ ❦ ✦ ❦</div>

        <form method="get" action="/">
          <div class="search-grid">
            <div class="field-group">
              <label class="field-label" for="query">Subreddits</label>
              <input
                id="query"
                type="text"
                name="query"
                placeholder="e.g. wallpapers, linux"
                value="{{ query }}"
              >
              <span class="field-footer-line"></span>
            </div>

            <div class="field-group">
              <label class="field-label" for="subreddit">Exact subreddit</label>
              <input
                id="subreddit"
                type="text"
                name="subreddit"
                placeholder="e.g. funny"
                value="{{ subreddit }}"
              >
              <span class="field-footer-line"></span>
            </div>

            <div class="field-group">
              <label class="field-label" for="user_query">Users</label>
              <input
                id="user_query"
                type="text"
                name="user_query"
                placeholder="e.g. photographer"
                value="{{ user_query }}"
              >
              <span class="field-footer-line"></span>
            </div>

            <div class="field-group">
              <label class="field-label" for="username">Exact user</label>
              <input
                id="username"
                type="text"
                name="username"
                placeholder="e.g. spez"
                value="{{ username }}"
              >
              <span class="field-footer-line"></span>
            </div>
          </div>

          <div class="search-grid-secondary">
            <div class="field-group compact">
              <label class="field-label" for="sort">Sort</label>
              <select id="sort" name="sort">
                {% for value, label in sort_options %}
                  <option value="{{ value }}" {% if sort == value %}selected{% endif %}>{{ label }}</option>
                {% endfor %}
              </select>
              <span class="field-footer-line"></span>
            </div>

            <div class="field-group compact {% if sort != 'top' %}is-hidden{% endif %}" id="top-time-group">
              <label class="field-label" for="top_time">Top range</label>
              <select id="top_time" name="top_time">
                {% for value, label in top_time_options %}
                  <option value="{{ value }}" {% if top_time == value %}selected{% endif %}>{{ label }}</option>
                {% endfor %}
              </select>
              <span class="field-footer-line"></span>
            </div>
          </div>

          <div class="actions-row">
            <div class="actions-left">
              <label class="checkbox">
                <input id="over18-checkbox" type="checkbox" name="over18" value="1" {% if over18 %}checked{% endif %}>
                <span>I'm over 18 and want mature content when Reddit allows guest access</span>
              </label>
            </div>

            <div class="actions-right">
              <span id="nsfw-badge" class="nsfw-badge {% if not over18 %}is-hidden{% endif %}">NSFW</span>
              <button type="submit">Open Viewer</button>
            </div>
          </div>
        </form>

        <div class="menu-ornament-bottom">✦ ❦ ✦ ❦ ✦ ❦ ✦</div>
      </div>

      {% if search_results or user_results %}
        <div class="results-showcase">
          <div class="split">
            <div class="results-panel">
              <h2 class="section-title"><span>Subreddit results</span></h2>
              <div class="results-divider"></div>
              {% if search_results %}
                <div class="results-grid">
                  {% for result in search_results %}
                    <a class="result-card" href="/?subreddit={{ result['display_name']|urlencode }}&sort={{ sort }}{% if sort == 'top' %}&top_time={{ top_time|urlencode }}{% endif %}{% if over18 %}&over18=1{% endif %}">
                      <span class="result-title">r/{{ result['display_name'] }}</span>
                      <div class="result-line"></div>
                      <small>
                        {% if result['over18'] %}18+ · {% endif %}
                        {% if result['subscribers'] is not none %}{{ '{:,}'.format(result['subscribers']) }} members{% else %}member count unavailable{% endif %}
                      </small>
                    </a>
                  {% endfor %}
                </div>
              {% else %}
                <div class="notice">No subreddit matches found.</div>
              {% endif %}
            </div>

            <div class="results-panel">
              <h2 class="section-title"><span>User results</span></h2>
              <div class="results-divider"></div>
              {% if user_results %}
                <div class="results-grid">
                  {% for result in user_results %}
                    <a class="result-card" href="/?username={{ result['name']|urlencode }}&sort={{ sort }}{% if sort == 'top' %}&top_time={{ top_time|urlencode }}{% endif %}{% if over18 %}&over18=1{% endif %}">
                      <span class="result-title">u/{{ result['name'] }}</span>
                      <div class="result-line"></div>
                      <small>
                        {% if result['total_karma'] is not none %}{{ '{:,}'.format(result['total_karma']) }} karma{% else %}karma unavailable{% endif %}
                        {% if result['is_nsfw'] %} · 18+ profile{% endif %}
                      </small>
                    </a>
                  {% endfor %}
                </div>
              {% else %}
                <div class="notice">No user matches found.</div>
              {% endif %}
            </div>
          </div>
        </div>
      {% endif %}
    </div>

    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}

    {% if active_view == 'subreddit' and subreddit and posts is not none %}
      <div class="card toolbar-card browser-results-panel">
        <div class="toolbar">
          <div class="toolbar-left">
            <h2 style="font-size:1.35rem;">r/{{ subreddit }}</h2>
            <span class="button-link muted">
              {% if sort == 'top' %}
                Top · {{ top_time_label }}
              {% else %}
                {{ current_sort_label }}
              {% endif %}
            </span>
            {% if subreddit_meta and subreddit_meta.get('over18') %}
              <span class="button-link muted">18+</span>
            {% endif %}
            <span class="button-link muted">{{ media_count }} {% if results_query %}matching {% endif %}media item{% if media_count != 1 %}s{% endif %}</span>
            <span class="button-link muted js-post-count">{{ posts|length }} post{% if posts|length != 1 %}s{% endif %} on this page</span>
            <form class="results-search" method="get" action="/" data-results-search>
              <input type="hidden" name="subreddit" value="{{ subreddit }}">
              <input type="hidden" name="sort" value="{{ sort }}">
              {% if sort == 'top' %}<input type="hidden" name="top_time" value="{{ top_time }}">{% endif %}
              {% if over18 %}<input type="hidden" name="over18" value="1">{% endif %}
              <input type="hidden" name="results_query" value="{{ results_query }}" data-results-search-submit>
              <label class="sr-only" for="results-query-subreddit">Filter this page or run an extended subreddit search</label>
              <input id="results-query-subreddit" class="results-search-input" type="search" value="{{ results_query }}" placeholder="Search this page" autocomplete="off" spellcheck="false" data-results-search-input>
              <button type="submit" class="results-search-button">Extended search</button>
              {% if results_query %}
                <a class="results-search-clear" href="/?subreddit={{ subreddit|urlencode }}&sort={{ sort }}{% if sort == 'top' %}&top_time={{ top_time|urlencode }}{% endif %}{% if over18 %}&over18=1{% endif %}">Clear extended</a>
              {% endif %}
            </form>
          </div>
          <div class="toolbar-left">
            {% if next_after %}
              <a class="button-link muted" href="/?subreddit={{ subreddit|urlencode }}&sort={{ sort }}{% if sort == 'top' %}&top_time={{ top_time|urlencode }}{% endif %}&after={{ next_after|urlencode }}{% if over18 %}&over18=1{% endif %}{% if results_query %}&results_query={{ results_query|urlencode }}{% endif %}">Next page</a>
            {% endif %}
            <a class="button-link muted" target="_blank" rel="noopener noreferrer" href="https://www.reddit.com/r/{{ subreddit|urlencode }}/{{ api_sort }}/{% if sort == 'top' %}?t={{ top_time|urlencode }}{% endif %}">Open on Reddit</a>
          </div>
        </div>

        {% if subreddit_meta and subreddit_meta.get('public_description') %}
          <p class="muted-line">{{ subreddit_meta.get('public_description') }}</p>
        {% endif %}

        {% if results_query %}
          <p class="muted-line results-search-meta">Showing extended-search matches for “{{ results_query }}” across r/{{ subreddit }} · scanned {{ search_pages_fetched }} API page{% if search_pages_fetched != 1 %}s{% endif %}</p>
        {% endif %}

        {% if search_limit_hit %}
          <div class="notice">Search stopped after scanning {{ search_pages_fetched }} API pages. Narrow the search if you need deeper results.</div>
        {% endif %}

        {% if posts %}
          <div class="gallery">
            {% for post in posts %}
              {% set first_media = post['media_items'][0] %}
              {% set first_download_url = media_download_url(first_media) %}
              {% set first_download_filename = build_download_filename(post['title'], first_media) %}
              <div class="tile" data-media-carousel data-active-index="0" data-search-text="{{ post.get('search_text', '')|e }}">
                <div class="media-shell media-carousel {% if post['media_items']|length > 1 %}has-multiple{% endif %}">
                  {% if post['media_items']|length > 1 %}
                    <span class="media-count-badge">{{ post['media_items']|length }} media</span>
                  {% endif %}
                  {% for media in post['media_items'] %}
                    {% set download_url = media_download_url(media) %}
                    {% set download_filename = build_download_filename(post['title'], media) %}
                    <div class="media-slide {% if loop.first %}is-active{% endif %}" data-media-slide data-media-label="{{ media['label']|e }}" {% if download_url %}data-download-href="/download?url={{ download_url|urlencode }}&filename={{ download_filename|urlencode }}{% if media.get('dash_url') %}&dash_url={{ media['dash_url']|urlencode }}{% endif %}"{% endif %} aria-hidden="{% if loop.first %}false{% else %}true{% endif %}">
                      {% if media['kind'] == 'image' %}
                        <a href="{{ media['url'] }}" target="_blank" rel="noopener noreferrer">
                          <img class="media-frame" loading="lazy" src="{{ media['url'] }}" alt="{{ post['title'] }}">
                        </a>
                      {% elif media['kind'] == 'gifv' %}
                        <span class="media-pill">GIF / clip</span>
                        <video
                          class="media-frame deferred-video"
                          {% if media.get('poster') %}poster="{{ media['poster'] }}"{% endif %}
                          preload="none"
                          muted
                          loop
                          playsinline
                          data-kind="gifv"
                          {% if media.get('mp4_url') %}data-mp4-url="{{ media['mp4_url'] }}"{% endif %}
                          {% if media.get('webm_url') %}data-webm-url="{{ media['webm_url'] }}"{% endif %}
                        >
                          {% if media.get('mp4_url') %}<source data-src="{{ media['mp4_url'] }}" type="video/mp4">{% endif %}
                          {% if media.get('webm_url') %}<source data-src="{{ media['webm_url'] }}" type="video/webm">{% endif %}
                        </video>
                        <button type="button" class="media-load-btn" data-autoplay="1">Play clip</button>
                      {% else %}
                        <span class="media-pill">Video</span>
                        <video
                          class="media-frame deferred-video"
                          {% if media.get('poster') %}poster="{{ media['poster'] }}"{% endif %}
                          controls
                          preload="none"
                          playsinline
                          data-kind="video"
                          {% if media.get('dash_url') %}data-dash-url="{{ media['dash_url'] }}"{% endif %}
                          {% if media.get('hls_url') %}data-hls-url="{{ media['hls_url'] }}"{% endif %}
                          {% if media.get('mp4_url') %}data-mp4-url="{{ media['mp4_url'] }}"{% endif %}
                          {% if media.get('webm_url') %}data-webm-url="{{ media['webm_url'] }}"{% endif %}
                        >
                          {% if media.get('mp4_url') %}<source data-src="{{ media['mp4_url'] }}" type="video/mp4">{% endif %}
                          {% if media.get('webm_url') %}<source data-src="{{ media['webm_url'] }}" type="video/webm">{% endif %}
                          Sorry, your browser could not play this video.
                        </video>
                        <button type="button" class="media-load-btn" data-autoplay="1">Play video</button>
                      {% endif %}
                    </div>
                  {% endfor %}
                  {% if post['media_items']|length > 1 %}
                    <div class="media-carousel-nav">
                      <button type="button" class="media-nav-button" data-carousel-prev aria-label="Previous media">‹</button>
                      <span class="media-nav-status" data-carousel-status>1 / {{ post['media_items']|length }}</span>
                      <button type="button" class="media-nav-button" data-carousel-next aria-label="Next media">›</button>
                    </div>
                  {% endif %}
                </div>

                <div class="tile-body">
                  <div class="title">{{ post['title'] }}</div>
                  <div class="meta">
                    by u/{{ post['author'] }} · <span data-active-media-label>{{ first_media['label'] }}</span>{% if post['media_items']|length > 1 %} · {{ post['media_items']|length }} files{% endif %}{% if post['is_nsfw'] %} · NSFW{% endif %}
                  </div>
                  <div class="tile-actions">
                    {% if first_download_url %}
                      <a class="tile-action-button" data-download-button href="/download?url={{ first_download_url|urlencode }}&filename={{ first_download_filename|urlencode }}{% if first_media.get('dash_url') %}&dash_url={{ first_media['dash_url']|urlencode }}{% endif %}">Download</a>
                    {% endif %}
                    <button type="button" class="tile-action-button secondary view-user-btn" data-username="{{ post['author']|e }}">View user</button>
                  </div>
                </div>
              </div>
            {% endfor %}
          </div>
          <div class="notice is-hidden" data-results-filter-empty>No posts on this page matched your search.</div>
        {% else %}
          {% if results_query %}<div class="notice">No matching media posts were found in r/{{ subreddit }} for “{{ results_query }}”.</div>{% else %}<div class="notice">No supported media posts were found in this listing.</div>{% endif %}
        {% endif %}

        {% if next_after %}
          <div class="pagination-footer">
            <a class="button-link muted" href="/?subreddit={{ subreddit|urlencode }}&sort={{ sort }}{% if sort == 'top' %}&top_time={{ top_time|urlencode }}{% endif %}&after={{ next_after|urlencode }}{% if over18 %}&over18=1{% endif %}{% if results_query %}&results_query={{ results_query|urlencode }}{% endif %}">Next page</a>
          </div>
        {% endif %}
      </div>
    {% endif %}

    {% if active_view == 'user' and username and posts is not none %}
      <div class="card toolbar-card browser-results-panel">
        <div class="toolbar">
          <div class="toolbar-left">
            <h2 style="font-size:1.35rem;">u/{{ username }}</h2>
            <span class="button-link muted">
              {% if sort == 'top' %}
                Top · {{ top_time_label }}
              {% else %}
                {{ current_sort_label }}
              {% endif %}
            </span>
            <span class="button-link muted">{{ media_count }} {% if results_query %}matching {% endif %}media item{% if media_count != 1 %}s{% endif %}</span>
            <span class="button-link muted js-post-count">{{ posts|length }} post{% if posts|length != 1 %}s{% endif %} on this page</span>
            <form class="results-search" method="get" action="/" data-results-search>
              <input type="hidden" name="username" value="{{ username }}">
              <input type="hidden" name="sort" value="{{ sort }}">
              {% if sort == 'top' %}<input type="hidden" name="top_time" value="{{ top_time }}">{% endif %}
              {% if over18 %}<input type="hidden" name="over18" value="1">{% endif %}
              <input type="hidden" name="results_query" value="{{ results_query }}" data-results-search-submit>
              <label class="sr-only" for="results-query-user">Filter this page or run an extended user search</label>
              <input id="results-query-user" class="results-search-input" type="search" value="{{ results_query }}" placeholder="Search this page" autocomplete="off" spellcheck="false" data-results-search-input>
              <button type="submit" class="results-search-button">Extended search</button>
              {% if results_query %}
                <a class="results-search-clear" href="/?username={{ username|urlencode }}&sort={{ sort }}{% if sort == 'top' %}&top_time={{ top_time|urlencode }}{% endif %}{% if over18 %}&over18=1{% endif %}">Clear extended</a>
              {% endif %}
            </form>
          </div>
          <div class="toolbar-left">
            {% if next_after %}
              <a class="button-link muted" href="/?username={{ username|urlencode }}&sort={{ sort }}{% if sort == 'top' %}&top_time={{ top_time|urlencode }}{% endif %}&after={{ next_after|urlencode }}{% if over18 %}&over18=1{% endif %}{% if results_query %}&results_query={{ results_query|urlencode }}{% endif %}">Next page</a>
            {% endif %}
            <a class="button-link muted" target="_blank" rel="noopener noreferrer" href="https://www.reddit.com/user/{{ username|urlencode }}/submitted/">Open on Reddit</a>
          </div>
        </div>

        {% if user_meta %}
          <p class="muted-line">
            {% if user_meta.get('total_karma') is not none %}{{ '{:,}'.format(user_meta.get('total_karma')) }} karma{% endif %}
            {% if user_meta.get('link_karma') is not none and user_meta.get('comment_karma') is not none %}
              · {{ '{:,}'.format(user_meta.get('link_karma')) }} link karma
              · {{ '{:,}'.format(user_meta.get('comment_karma')) }} comment karma
            {% endif %}
          </p>
        {% endif %}

        {% if results_query %}
          <p class="muted-line results-search-meta">Showing extended-search matches for “{{ results_query }}” across u/{{ username }} · scanned {{ search_pages_fetched }} API page{% if search_pages_fetched != 1 %}s{% endif %}</p>
        {% endif %}

        {% if search_limit_hit %}
          <div class="notice">Search stopped after scanning {{ search_pages_fetched }} API pages. Narrow the search if you need deeper results.</div>
        {% endif %}

        {% if posts %}
          <div class="gallery">
            {% for post in posts %}
              {% set first_media = post['media_items'][0] %}
              {% set first_download_url = media_download_url(first_media) %}
              {% set first_download_filename = build_download_filename(post['title'], first_media) %}
              <div class="tile" data-media-carousel data-active-index="0" data-search-text="{{ post.get('search_text', '')|e }}">
                <div class="media-shell media-carousel {% if post['media_items']|length > 1 %}has-multiple{% endif %}">
                  {% if post['media_items']|length > 1 %}
                    <span class="media-count-badge">{{ post['media_items']|length }} media</span>
                  {% endif %}
                  {% for media in post['media_items'] %}
                    {% set download_url = media_download_url(media) %}
                    {% set download_filename = build_download_filename(post['title'], media) %}
                    <div class="media-slide {% if loop.first %}is-active{% endif %}" data-media-slide data-media-label="{{ media['label']|e }}" {% if download_url %}data-download-href="/download?url={{ download_url|urlencode }}&filename={{ download_filename|urlencode }}{% if media.get('dash_url') %}&dash_url={{ media['dash_url']|urlencode }}{% endif %}"{% endif %} aria-hidden="{% if loop.first %}false{% else %}true{% endif %}">
                      {% if media['kind'] == 'image' %}
                        <a href="{{ media['url'] }}" target="_blank" rel="noopener noreferrer">
                          <img class="media-frame" loading="lazy" src="{{ media['url'] }}" alt="{{ post['title'] }}">
                        </a>
                      {% elif media['kind'] == 'gifv' %}
                        <span class="media-pill">GIF / clip</span>
                        <video
                          class="media-frame deferred-video"
                          {% if media.get('poster') %}poster="{{ media['poster'] }}"{% endif %}
                          preload="none"
                          muted
                          loop
                          playsinline
                          data-kind="gifv"
                          {% if media.get('mp4_url') %}data-mp4-url="{{ media['mp4_url'] }}"{% endif %}
                          {% if media.get('webm_url') %}data-webm-url="{{ media['webm_url'] }}"{% endif %}
                        >
                          {% if media.get('mp4_url') %}<source data-src="{{ media['mp4_url'] }}" type="video/mp4">{% endif %}
                          {% if media.get('webm_url') %}<source data-src="{{ media['webm_url'] }}" type="video/webm">{% endif %}
                        </video>
                        <button type="button" class="media-load-btn" data-autoplay="1">Play clip</button>
                      {% else %}
                        <span class="media-pill">Video</span>
                        <video
                          class="media-frame deferred-video"
                          {% if media.get('poster') %}poster="{{ media['poster'] }}"{% endif %}
                          controls
                          preload="none"
                          playsinline
                          data-kind="video"
                          {% if media.get('dash_url') %}data-dash-url="{{ media['dash_url'] }}"{% endif %}
                          {% if media.get('hls_url') %}data-hls-url="{{ media['hls_url'] }}"{% endif %}
                          {% if media.get('mp4_url') %}data-mp4-url="{{ media['mp4_url'] }}"{% endif %}
                          {% if media.get('webm_url') %}data-webm-url="{{ media['webm_url'] }}"{% endif %}
                        >
                          {% if media.get('mp4_url') %}<source data-src="{{ media['mp4_url'] }}" type="video/mp4">{% endif %}
                          {% if media.get('webm_url') %}<source data-src="{{ media['webm_url'] }}" type="video/webm">{% endif %}
                          Sorry, your browser could not play this video.
                        </video>
                        <button type="button" class="media-load-btn" data-autoplay="1">Play video</button>
                      {% endif %}
                    </div>
                  {% endfor %}
                  {% if post['media_items']|length > 1 %}
                    <div class="media-carousel-nav">
                      <button type="button" class="media-nav-button" data-carousel-prev aria-label="Previous media">‹</button>
                      <span class="media-nav-status" data-carousel-status>1 / {{ post['media_items']|length }}</span>
                      <button type="button" class="media-nav-button" data-carousel-next aria-label="Next media">›</button>
                    </div>
                  {% endif %}
                </div>

                <div class="tile-body">
                  <div class="title">{{ post['title'] }}</div>
                  <div class="meta">
                    posted to r/{{ post['subreddit'] }} · <span data-active-media-label>{{ first_media['label'] }}</span>{% if post['media_items']|length > 1 %} · {{ post['media_items']|length }} files{% endif %}{% if post['is_nsfw'] %} · NSFW{% endif %}
                  </div>
                  <div class="tile-actions">
                    {% if first_download_url %}
                      <a class="tile-action-button" data-download-button href="/download?url={{ first_download_url|urlencode }}&filename={{ first_download_filename|urlencode }}{% if first_media.get('dash_url') %}&dash_url={{ first_media['dash_url']|urlencode }}{% endif %}">Download</a>
                    {% endif %}
                    <button type="button" class="tile-action-button secondary view-user-btn" data-username="{{ post['author']|e }}">View user</button>
                  </div>
                </div>
              </div>
            {% endfor %}
          </div>
          <div class="notice is-hidden" data-results-filter-empty>No posts on this page matched your search.</div>
        {% else %}
          {% if results_query %}<div class="notice">No matching media posts were found for u/{{ username }} for “{{ results_query }}”.</div>{% else %}<div class="notice">No supported media posts were found for this user.</div>{% endif %}
        {% endif %}
        {% if next_after %}
          <div class="pagination-footer">
            <a class="button-link muted" href="/?username={{ username|urlencode }}&sort={{ sort }}{% if sort == 'top' %}&top_time={{ top_time|urlencode }}{% endif %}&after={{ next_after|urlencode }}{% if over18 %}&over18=1{% endif %}{% if results_query %}&results_query={{ results_query|urlencode }}{% endif %}">Next page</a>
          </div>
        {% endif %}
      </div>
    {% endif %}
  <script src="https://cdn.dashjs.org/latest/modern/umd/dash.all.min.js"></script>
  <script>
    (() => {
      const sortSelect = document.getElementById("sort");
      const topTimeGroup = document.getElementById("top-time-group");
      const matureCheckbox = document.getElementById("over18-checkbox");
      const nsfwBadge = document.getElementById("nsfw-badge");
      const usernameField = document.getElementById("username");
      const subredditField = document.getElementById("subreddit");

      function updateTopTimeVisibility() {
        if (!sortSelect || !topTimeGroup) return;

        if (sortSelect.value === "top") {
          topTimeGroup.classList.remove("is-hidden");
        } else {
          topTimeGroup.classList.add("is-hidden");
        }
      }

      function updateNsfwBadgeVisibility() {
        if (!matureCheckbox || !nsfwBadge) return;

        if (matureCheckbox.checked) {
          nsfwBadge.classList.remove("is-hidden");
        } else {
          nsfwBadge.classList.add("is-hidden");
        }
      }

      function highlightUsernameField() {
        if (!usernameField) return;
        usernameField.classList.add("field-highlight");
        window.setTimeout(() => {
          usernameField.classList.remove("field-highlight");
        }, 1400);
      }

      if (sortSelect) {
        sortSelect.addEventListener("change", updateTopTimeVisibility);
        updateTopTimeVisibility();
      }

      if (matureCheckbox) {
        matureCheckbox.addEventListener("change", updateNsfwBadgeVisibility);
        updateNsfwBadgeVisibility();
      }

      function destroyManagedPlayer(video) {
        if (video && video._dashPlayer) {
          try {
            video._dashPlayer.reset();
          } catch (_) {}
          video._dashPlayer = null;
        }
      }

      function ensureVideoAudioState(video) {
        if (!video || video.dataset.kind !== "video") return;
        video.muted = false;
        video.defaultMuted = false;
        video.removeAttribute("muted");
        try {
          video.volume = 1;
        } catch (_) {}
      }

      function loadDeferredVideo(video, autoplay = false) {
        if (!video) return;

        if (video.dataset.loaded === "1") {
          ensureVideoAudioState(video);
          if (autoplay) {
            const playPromise = video.play();
            if (playPromise) playPromise.catch(() => {});
          }
          return;
        }

        const shell = video.closest(".media-shell");
        const dashUrl = video.dataset.dashUrl;

        if (video.dataset.kind === "video" && dashUrl && window.dashjs) {
          try {
            destroyManagedPlayer(video);
            const player = dashjs.MediaPlayer().create();
            player.initialize(video, dashUrl, false);
            video._dashPlayer = player;
            video.dataset.loaded = "1";
            ensureVideoAudioState(video);
            if (shell) shell.classList.add("is-loaded");

            if (autoplay) {
              const playPromise = video.play();
              if (playPromise) playPromise.catch(() => {});
            }
            return;
          } catch (err) {
            console.error("dash.js failed, falling back to plain video sources", err);
          }
        }

        const sources = video.querySelectorAll("source[data-src]");
        let hasSource = false;

        sources.forEach((source) => {
          const src = source.getAttribute("data-src");
          if (src) {
            source.setAttribute("src", src);
            hasSource = true;
          }
        });

        if (!hasSource) return;

        video.load();
        video.dataset.loaded = "1";
        if (video.dataset.kind === "gifv") {
          video.muted = true;
        } else {
          ensureVideoAudioState(video);
        }

        if (shell) shell.classList.add("is-loaded");

        if (autoplay) {
          const playPromise = video.play();
          if (playPromise) playPromise.catch(() => {});
        }
      }

      function pauseOtherGifv(currentVideo) {
        document.querySelectorAll('video.deferred-video[data-kind="gifv"]').forEach((video) => {
          if (video !== currentVideo && !video.paused) {
            video.pause();
          }
        });
      }

      function pauseVideosInSlide(slide) {
        if (!slide) return;
        slide.querySelectorAll("video.deferred-video").forEach((video) => {
          if (!video.paused) {
            video.pause();
          }
        });
      }

      function setActiveCarouselSlide(tile, nextIndex) {
        if (!tile) return;

        const slides = Array.from(tile.querySelectorAll("[data-media-slide]"));
        if (!slides.length) return;

        const total = slides.length;
        const currentIndex = Number(tile.dataset.activeIndex || 0);
        const safeIndex = ((nextIndex % total) + total) % total;

        if (slides[currentIndex] && currentIndex !== safeIndex) {
          pauseVideosInSlide(slides[currentIndex]);
        }

        slides.forEach((slide, index) => {
          const isActive = index === safeIndex;
          slide.classList.toggle("is-active", isActive);
          slide.setAttribute("aria-hidden", isActive ? "false" : "true");
        });

        tile.dataset.activeIndex = String(safeIndex);

        const activeSlide = slides[safeIndex];
        const activeVideo = activeSlide.querySelector('video.deferred-video[data-kind="video"]');
        if (activeVideo && activeVideo.dataset.loaded === "1") {
          ensureVideoAudioState(activeVideo);
        }

        const counter = tile.querySelector("[data-carousel-status]");
        const label = tile.querySelector("[data-active-media-label]");
        const downloadButton = tile.querySelector("[data-download-button]");

        if (counter) {
          counter.textContent = `${safeIndex + 1} / ${total}`;
        }

        if (label) {
          label.textContent = activeSlide.dataset.mediaLabel || "media";
        }

        if (downloadButton) {
          const href = activeSlide.dataset.downloadHref || "";
          if (href) {
            downloadButton.setAttribute("href", href);
            downloadButton.classList.remove("is-hidden");
          } else {
            downloadButton.removeAttribute("href");
            downloadButton.classList.add("is-hidden");
          }
        }
      }

      document.querySelectorAll("[data-media-carousel]").forEach((tile) => {
        setActiveCarouselSlide(tile, Number(tile.dataset.activeIndex || 0));
      });

      document.addEventListener("click", (event) => {
        const button = event.target.closest(".media-load-btn");
        if (!button) return;

        const shell = button.closest(".media-shell");
        if (!shell) return;

        const activeSlide = shell.querySelector(".media-slide.is-active");
        const video = (activeSlide || shell).querySelector("video.deferred-video");
        if (!video) return;

        const autoplay = button.dataset.autoplay === "1";

        if (video.dataset.kind === "gifv" && autoplay) {
          pauseOtherGifv(video);
        }

        ensureVideoAudioState(video);
        loadDeferredVideo(video, autoplay);
      });

      document.addEventListener("click", (event) => {
        const carouselButton = event.target.closest("[data-carousel-prev], [data-carousel-next]");
        if (!carouselButton) return;

        const tile = carouselButton.closest("[data-media-carousel]");
        if (!tile) return;

        const currentIndex = Number(tile.dataset.activeIndex || 0);
        const delta = carouselButton.hasAttribute("data-carousel-next") ? 1 : -1;
        setActiveCarouselSlide(tile, currentIndex + delta);
      });

      document.addEventListener("click", (event) => {
        const viewUserButton = event.target.closest(".view-user-btn");
        if (!viewUserButton) return;

        const username = (viewUserButton.dataset.username || "").trim();
        if (!username || !usernameField) return;

        usernameField.value = username;

        if (subredditField) {
          subredditField.value = "";
        }

        usernameField.focus();
        usernameField.select();
        usernameField.scrollIntoView({
          behavior: "smooth",
          block: "center"
        });

        highlightUsernameField();
      });

      const resultsPanel = document.querySelector(".browser-results-panel");
      const resultsSearch = resultsPanel ? resultsPanel.querySelector("[data-results-search]") : null;
      const resultsSearchInput = resultsSearch ? resultsSearch.querySelector("[data-results-search-input]") : null;
      const resultsSearchSubmitField = resultsSearch ? resultsSearch.querySelector("[data-results-search-submit]") : null;
      const postCountBadge = resultsPanel ? resultsPanel.querySelector(".js-post-count") : null;
      const filterEmptyNotice = resultsPanel ? resultsPanel.querySelector("[data-results-filter-empty]") : null;
      const resultTiles = resultsPanel ? Array.from(resultsPanel.querySelectorAll(".tile[data-search-text]")) : [];

      function updatePostCountBadge(visibleCount, totalCount) {
        if (!postCountBadge) return;

        const hasActiveFilter = resultsSearchInput && resultsSearchInput.value.trim() !== "";
        const postLabel = totalCount === 1 ? "post" : "posts";

        if (hasActiveFilter) {
          postCountBadge.textContent = `${visibleCount} of ${totalCount} ${postLabel}`;
        } else {
          postCountBadge.textContent = `${totalCount} ${postLabel} on this page`;
        }
      }

      function applyResultsFilter() {
        if (!resultsSearchInput || !postCountBadge) return;

        const needle = resultsSearchInput.value.trim().toLowerCase();
        const totalCount = resultTiles.length;
        let visibleCount = 0;

        resultTiles.forEach((tile) => {
          const haystack = (tile.dataset.searchText || "").toLowerCase();
          const matches = !needle || haystack.includes(needle);

          tile.style.display = matches ? "" : "none";

          if (matches) {
            visibleCount += 1;
          }
        });

        if (filterEmptyNotice) {
          filterEmptyNotice.classList.toggle("is-hidden", !(needle && visibleCount === 0));
        }

        updatePostCountBadge(visibleCount, totalCount);
      }

      if (resultsSearchInput) {
        resultsSearchInput.addEventListener("input", applyResultsFilter);
        resultsSearchInput.addEventListener("search", applyResultsFilter);
      }

      if (resultsSearch) {
        resultsSearch.addEventListener("submit", () => {
          if (resultsSearchSubmitField) {
            resultsSearchSubmitField.value = resultsSearchInput ? resultsSearchInput.value.trim() : "";
          }
        });
      }

      document.addEventListener("click", (event) => {
        const video = event.target.closest('video.deferred-video[data-kind="gifv"]');
        if (!video || video.dataset.loaded !== "1") return;

        if (video.paused) {
          pauseOtherGifv(video);
          const playPromise = video.play();
          if (playPromise) playPromise.catch(() => {});
        } else {
          video.pause();
        }
      });

      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          const video = entry.target;
          if (!entry.isIntersecting && !video.paused) {
            video.pause();
          }
        });
      }, { threshold: 0.15 });

      document.querySelectorAll("video.deferred-video").forEach((video) => {
        observer.observe(video);
      });
    })();
  </script>
</body>
</html>
"""


@app.template_filter("urlencode")
def urlencode_filter(value: str) -> str:
    return quote(value, safe="")


class RedditClient:
    def __init__(self, over18: bool = False):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.over18 = over18
        if over18:
            self.session.cookies.set("over18", "1", domain=".reddit.com")

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code == 403:
            raise RuntimeError(
                "Reddit refused the request. The target may be private, quarantined, removed, or blocked for guest access in your region."
            )
        if response.status_code == 404:
            raise RuntimeError("That subreddit or user was not found.")
        if response.status_code == 429:
            raise RuntimeError("Rate limited by Reddit. Wait a bit, then try again.")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"Reddit returned an error: {data['error']}")
        return data

    def search_subreddits(self, query: str) -> list[dict[str, Any]]:
        params = {
            "q": query,
            "limit": MAX_SUBREDDIT_RESULTS,
            "include_over_18": "on" if self.over18 else "off",
            "raw_json": 1,
        }
        data = self._get("https://www.reddit.com/subreddits/search.json", params=params)
        results: list[dict[str, Any]] = []
        for child in data.get("data", {}).get("children", []):
            item = child.get("data", {})
            name = item.get("display_name")
            if not name:
                continue
            results.append(
                {
                    "display_name": name,
                    "subscribers": item.get("subscribers"),
                    "over18": bool(item.get("over18")),
                }
            )
        return results

    def search_users(self, query: str) -> list[dict[str, Any]]:
        params = {
            "q": query,
            "limit": MAX_USER_RESULTS,
            "raw_json": 1,
            "sort": "relevance",
        }
        data = self._get("https://www.reddit.com/users/search.json", params=params)
        results: list[dict[str, Any]] = []
        for child in data.get("data", {}).get("children", []):
            item = child.get("data", {})
            name = item.get("name")
            if not name:
                continue
            subreddit_info = item.get("subreddit") or {}
            results.append(
                {
                    "name": name,
                    "total_karma": item.get("total_karma"),
                    "is_nsfw": bool(subreddit_info.get("over_18")),
                }
            )
        return results

    def load_subreddit(
        self,
        subreddit: str,
        sort: str = "hot",
        after: str | None = None,
        limit: int = API_BATCH_SIZE,
        top_time: str = "all",
    ) -> dict[str, Any]:
        sort = sort if sort in {"best", "hot", "new", "top", "rising"} else "hot"
        params = {
            "limit": max(1, min(limit, 100)),
            "raw_json": 1,
        }
        if after:
            params["after"] = after
        if sort == "top":
            params["t"] = top_time if top_time in {"hour", "day", "week", "month", "year", "all"} else "all"
        return self._get(f"https://www.reddit.com/r/{quote(subreddit)}/{sort}.json", params=params)

    def load_subreddit_about(self, subreddit: str) -> dict[str, Any] | None:
        try:
            data = self._get(f"https://www.reddit.com/r/{quote(subreddit)}/about.json", params={"raw_json": 1})
            return data.get("data", {})
        except Exception:
            return None

    def load_user_submitted(
        self,
        username: str,
        sort: str = "new",
        after: str | None = None,
        limit: int = API_BATCH_SIZE,
        top_time: str = "all",
    ) -> dict[str, Any]:
        sort = sort if sort in {"hot", "new", "top", "controversial"} else "new"
        params = {
            "limit": max(1, min(limit, 100)),
            "raw_json": 1,
        }
        if after:
            params["after"] = after
        if sort == "top":
            params["t"] = top_time if top_time in {"hour", "day", "week", "month", "year", "all"} else "all"
        return self._get(f"https://www.reddit.com/user/{quote(username)}/submitted.json", params=params)

    def load_user_about(self, username: str) -> dict[str, Any] | None:
        try:
            data = self._get(f"https://www.reddit.com/user/{quote(username)}/about.json", params={"raw_json": 1})
            return data.get("data", {})
        except Exception:
            return None


    def search_subreddit_posts(
        self,
        subreddit: str,
        query: str,
        after: str | None = None,
        limit: int = API_BATCH_SIZE,
        sort: str = "relevance",
        top_time: str = "all",
    ) -> dict[str, Any]:
        sort = sort if sort in {"relevance", "hot", "top", "new", "comments"} else "relevance"
        params = {
            "q": query,
            "restrict_sr": "on",
            "type": "link",
            "limit": max(1, min(limit, 100)),
            "raw_json": 1,
            "sort": sort,
            "include_over_18": "on" if self.over18 else "off",
        }
        if after:
            params["after"] = after
        if sort == "top":
            params["t"] = top_time if top_time in {"hour", "day", "week", "month", "year", "all"} else "all"
        return self._get(f"https://www.reddit.com/r/{quote(subreddit)}/search.json", params=params)

    def search_user_posts(
        self,
        username: str,
        query: str,
        after: str | None = None,
        limit: int = API_BATCH_SIZE,
        sort: str = "relevance",
        top_time: str = "all",
    ) -> dict[str, Any]:
        sort = sort if sort in {"relevance", "hot", "top", "new", "comments"} else "relevance"
        author_query = f'author:"{username}" {query}'.strip()
        params = {
            "q": author_query,
            "type": "link",
            "limit": max(1, min(limit, 100)),
            "raw_json": 1,
            "sort": sort,
            "include_over_18": "on" if self.over18 else "off",
        }
        if after:
            params["after"] = after
        if sort == "top":
            params["t"] = top_time if top_time in {"hour", "day", "week", "month", "year", "all"} else "all"
        return self._get("https://www.reddit.com/search.json", params=params)


def normalise_url(url: str) -> str:
    return html.unescape(url).strip()


def canonical_media_url(url: str) -> str:
    clean = normalise_url(url)
    if not clean:
        return ""

    parts = urlsplit(clean)
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/")

    if path.lower().endswith(".gifv"):
        path = path[:-5] + ".mp4"

    return urlunsplit((scheme, netloc, path, "", ""))


def safe_download_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "", value or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(".")
    return cleaned[:120] or "reddit_media"


def ensure_mp4_filename(filename: str) -> str:
    base = safe_download_filename(filename or "reddit_video")
    lower = base.lower()
    for ext in (".mp4", ".webm", ".mov", ".m4v", ".mkv"):
        if lower.endswith(ext):
            base = base[:-len(ext)]
            break
    return f"{base}.mp4"


def build_temp_file_response(
    file_path: str,
    filename: str,
    *,
    content_type: str,
    cleanup_dir: str | None = None,
) -> Response:
    encoded_filename = quote(filename)

    def generate():
        try:
            with open(file_path, "rb") as handle:
                while True:
                    chunk = handle.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk
        finally:
            if cleanup_dir:
                shutil.rmtree(cleanup_dir, ignore_errors=True)

    response = Response(stream_with_context(generate()), content_type=content_type)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
    )
    return response


def build_muxed_reddit_video_download(dash_url: str, filename: str) -> tuple[str, str, str]:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError(
            "ffmpeg is required to download Reddit videos with sound. Install it with: sudo apt install ffmpeg"
        )

    temp_dir = tempfile.mkdtemp(prefix="reddit_media_")
    output_filename = ensure_mp4_filename(filename)
    output_path = os.path.join(temp_dir, output_filename)

    command = [
        ffmpeg_bin,
        "-y",
        "-loglevel",
        "error",
        "-user_agent",
        USER_AGENT,
        "-i",
        dash_url,
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c",
        "copy",
        output_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        error_tail = (result.stderr or "").strip()
        raise RuntimeError(
            "ffmpeg could not build the Reddit video with audio."
            + (f" Details: {error_tail}" if error_tail else "")
        )

    return temp_dir, output_path, output_filename


def media_download_url(media: dict[str, Any]) -> str:
    kind = media.get("kind")
    if kind == "image":
        return media.get("url") or ""
    if kind == "gifv":
        return (
            media.get("mp4_url")
            or media.get("webm_url")
            or media.get("hls_url")
            or media.get("dash_url")
            or ""
        )
    return (
        media.get("mp4_url")
        or media.get("webm_url")
        or media.get("hls_url")
        or media.get("dash_url")
        or ""
    )


def guess_download_extension(media: dict[str, Any]) -> str:
    download_url = media_download_url(media)
    path = urlsplit(download_url).path.lower()

    for ext in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS:
        if path.endswith(ext):
            return ext

    if media.get("kind") == "image":
        return ".jpg"

    return ".mp4"


def build_download_filename(title: str, media: dict[str, Any]) -> str:
    base = safe_download_filename(title or "reddit_media")
    ext = guess_download_extension(media)
    if not base.lower().endswith(ext.lower()):
        base += ext
    return base


IMG_RE = re.compile(r"https?://\S+?(?:\.jpg|\.jpeg|\.png|\.webp|\.gif)(?:\?\S*)?$", re.IGNORECASE)
VID_RE = re.compile(r"https?://\S+?(?:\.mp4|\.webm|\.mov|\.m4v)(?:\?\S*)?$", re.IGNORECASE)
GIFV_RE = re.compile(r"https?://\S+?\.gifv(?:\?\S*)?$", re.IGNORECASE)


def extract_poster(post: dict[str, Any]) -> str | None:
    preview = post.get("preview", {})
    images = preview.get("images", [])
    if images:
        source = images[0].get("source", {})
        url = source.get("url")
        if url:
            return normalise_url(url)
    return None


def media_identity(media: dict[str, Any]) -> tuple[str, str]:
    kind = media.get("kind", "unknown")

    if kind == "image":
        return ("image", canonical_media_url(media.get("url") or ""))

    if kind in {"video", "gifv"}:
        primary = (
            media.get("dash_url")
            or media.get("hls_url")
            or media.get("mp4_url")
            or media.get("webm_url")
            or ""
        )
        return (kind, canonical_media_url(primary))

    return (kind, "")


def extract_media(post: dict[str, Any]) -> list[dict[str, Any]]:
    media_items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    poster = extract_poster(post)

    def add_image(url: str, source: str, label: str = "image") -> None:
        clean = normalise_url(url)
        identity = ("image", canonical_media_url(clean))
        if not identity[1] or identity in seen:
            return
        seen.add(identity)
        media_items.append(
            {
                "kind": "image",
                "url": clean,
                "source": source,
                "label": label,
            }
        )

    def add_video(
        *,
        mp4_url: str | None = None,
        webm_url: str | None = None,
        hls_url: str | None = None,
        dash_url: str | None = None,
        source: str,
        label: str,
        kind: str = "video",
        poster_url: str | None = None,
    ) -> None:
        mp4_clean = normalise_url(mp4_url) if mp4_url else None
        webm_clean = normalise_url(webm_url) if webm_url else None
        hls_clean = normalise_url(hls_url) if hls_url else None
        dash_clean = normalise_url(dash_url) if dash_url else None

        identity = (
            kind,
            canonical_media_url(dash_clean or hls_clean or mp4_clean or webm_clean or ""),
        )
        if not identity[1] or identity in seen:
            return

        seen.add(identity)
        media_items.append(
            {
                "kind": kind,
                "mp4_url": mp4_clean,
                "webm_url": webm_clean,
                "hls_url": hls_clean,
                "dash_url": dash_clean,
                "source": source,
                "label": label,
                "poster": poster_url,
            }
        )

    if post.get("is_gallery") and isinstance(post.get("media_metadata"), dict):
        for media in post["media_metadata"].values():
            if media.get("e") != "Image":
                continue
            source = media.get("s", {})
            url = source.get("u")
            if url:
                add_image(url, "gallery", "gallery image")
        if media_items:
            return media_items

    for media_container_name in ("secure_media", "media"):
        container = post.get(media_container_name) or {}
        if not isinstance(container, dict):
            continue
        reddit_video = container.get("reddit_video") or {}
        if not isinstance(reddit_video, dict):
            continue
        if reddit_video.get("fallback_url") or reddit_video.get("hls_url") or reddit_video.get("dash_url"):
            add_video(
                mp4_url=reddit_video.get("fallback_url"),
                hls_url=reddit_video.get("hls_url"),
                dash_url=reddit_video.get("dash_url"),
                source=media_container_name,
                label="video",
                kind="video",
                poster_url=poster,
            )
    if media_items:
        return media_items

    direct_url = normalise_url(post.get("url_overridden_by_dest") or post.get("url") or "")
    lower = direct_url.lower()

    if direct_url and lower.endswith(GIFV_EXTENSIONS):
        add_video(
            mp4_url=direct_url[:-5] + ".mp4",
            source="direct_gifv",
            label="gif/video",
            kind="gifv",
            poster_url=poster,
        )
        return media_items

    if direct_url and GIFV_RE.match(direct_url):
        add_video(
            mp4_url=re.sub(r"\.gifv(\?.*)?$", ".mp4", direct_url, flags=re.IGNORECASE),
            source="direct_gifv",
            label="gif/video",
            kind="gifv",
            poster_url=poster,
        )
        return media_items

    if direct_url and lower.endswith(VIDEO_EXTENSIONS):
        add_video(
            mp4_url=direct_url,
            source="direct",
            label="video",
            kind="video",
            poster_url=poster,
        )
        return media_items

    if direct_url and VID_RE.match(direct_url):
        add_video(
            mp4_url=direct_url,
            source="direct",
            label="video",
            kind="video",
            poster_url=poster,
        )
        return media_items

    if direct_url and lower.endswith(IMAGE_EXTENSIONS):
        add_image(direct_url, "direct", "image")
        return media_items

    if direct_url and IMG_RE.match(direct_url):
        add_image(direct_url, "direct", "image")
        return media_items

    preview = post.get("preview", {})

    reddit_video_preview = preview.get("reddit_video_preview") or {}
    if isinstance(reddit_video_preview, dict) and reddit_video_preview.get("fallback_url"):
        add_video(
            mp4_url=reddit_video_preview.get("fallback_url"),
            hls_url=reddit_video_preview.get("hls_url"),
            dash_url=reddit_video_preview.get("dash_url"),
            source="reddit_video_preview",
            label="gif/video",
            kind="gifv",
            poster_url=poster,
        )
        if media_items:
            return media_items

    for image in preview.get("images", []):
        source = image.get("source", {})
        url = source.get("url")
        if url:
            add_image(url, "preview", "image")

    return media_items


def normalise_search_query(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def ui_sort_to_search_sort(sort: str) -> str:
    mapping = {
        "best": "relevance",
        "hot": "hot",
        "rising": "hot",
        "new": "new",
        "top": "top",
    }
    return mapping.get((sort or "").lower(), "relevance")


def build_media_search_text(post: dict[str, Any], media: dict[str, Any]) -> str:
    author = str(post.get("author") or "unknown")
    subreddit = str(post.get("subreddit") or "unknown")
    parts = [
        post.get("title") or "",
        post.get("selftext") or "",
        author,
        f"u/{author}",
        subreddit,
        f"r/{subreddit}",
        post.get("link_flair_text") or "",
        post.get("domain") or "",
        post.get("url") or "",
        post.get("url_overridden_by_dest") or "",
        media.get("label") or "",
        media.get("kind") or "",
    ]
    if post.get("over_18"):
        parts.append("nsfw")
    return normalise_search_query(" ".join(str(part) for part in parts if part))


def build_post_search_text(post: dict[str, Any], media_items: list[dict[str, Any]]) -> str:
    joined = " ".join(build_media_search_text(post, media) for media in media_items)
    return normalise_search_query(joined)


def collect_unique_posts(
    fetch_page,
    *,
    initial_after: str | None = None,
    target_media_items: int = DISPLAY_MEDIA_ITEMS_PER_PAGE,
    max_api_pages: int = MAX_API_PAGES_PER_VIEW,
) -> tuple[list[dict[str, Any]], str | None, int, int, bool]:
    posts: list[dict[str, Any]] = []
    seen_media: set[tuple[str, str]] = set()
    after_token = initial_after
    pages_fetched = 0
    next_after: str | None = None
    media_count = 0
    search_limit_hit = False

    while media_count < target_media_items and pages_fetched < max_api_pages:
        listing = fetch_page(after=after_token, limit=API_BATCH_SIZE)
        pages_fetched += 1

        data = listing.get("data", {})
        children = data.get("children", [])
        api_after = data.get("after")

        if not children:
            next_after = None
            break

        for child in children:
            raw = child.get("data", {})
            post_name = raw.get("name") or api_after

            media_items = extract_media(raw)
            if not media_items:
                continue

            unique_media_items: list[dict[str, Any]] = []

            for media in media_items:
                identity = media_identity(media)
                if not identity[1]:
                    continue
                if identity in seen_media:
                    continue

                seen_media.add(identity)
                unique_media_items.append(dict(media))

            if not unique_media_items:
                continue

            media_count += len(unique_media_items)

            posts.append(
                {
                    "title": raw.get("title") or "Untitled",
                    "author": raw.get("author") or "unknown",
                    "subreddit": raw.get("subreddit") or "unknown",
                    "is_nsfw": bool(raw.get("over_18")),
                    "media_items": unique_media_items,
                    "search_text": build_post_search_text(raw, unique_media_items),
                }
            )

            if media_count >= target_media_items:
                next_after = post_name or api_after
                break

        if media_count >= target_media_items:
            break

        if not api_after:
            next_after = None
            break

        after_token = api_after
        next_after = api_after
    else:
        if pages_fetched >= max_api_pages and media_count < target_media_items:
            search_limit_hit = True

    return posts, next_after, media_count, pages_fetched, search_limit_hit


@app.route("/download")
def download_media():
    media_url = (request.args.get("url") or "").strip()
    requested_filename = (request.args.get("filename") or "reddit_media").strip()
    dash_url = (request.args.get("dash_url") or "").strip()

    if not media_url and not dash_url:
        return ("Missing media URL.", 400)

    filename = safe_download_filename(requested_filename)

    if dash_url:
        dash_parts = urlsplit(dash_url)
        if dash_parts.scheme not in {"http", "https"} or not dash_parts.netloc:
            return ("Invalid DASH URL.", 400)

        try:
            temp_dir, output_path, output_filename = build_muxed_reddit_video_download(
                dash_url,
                filename,
            )
            return build_temp_file_response(
                output_path,
                output_filename,
                content_type="video/mp4",
                cleanup_dir=temp_dir,
            )
        except Exception as exc:
            return (f"Download failed: {exc}", 500)

    parts = urlsplit(media_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return ("Invalid media URL.", 400)

    try:
        upstream = requests.get(
            media_url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            stream=True,
        )

        if upstream.status_code == 403:
            upstream.close()
            return ("Reddit refused the download request.", 403)
        if upstream.status_code == 404:
            upstream.close()
            return ("That media file was not found.", 404)
        if upstream.status_code == 429:
            upstream.close()
            return ("Rate limited by Reddit. Wait a bit, then try again.", 429)

        upstream.raise_for_status()

        content_type = upstream.headers.get("Content-Type", "application/octet-stream")
        encoded_filename = quote(filename)

        def generate():
            try:
                for chunk in upstream.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        response = Response(stream_with_context(generate()), content_type=content_type)
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
        )
        return response
    except requests.RequestException as exc:
        return (f"Download failed: {exc}", 502)


@app.route("/")
def index():
    query = (request.args.get("query") or "").strip()
    subreddit = (request.args.get("subreddit") or "").strip().removeprefix("r/")
    user_query = (request.args.get("user_query") or "").strip()
    username = (request.args.get("username") or "").strip().removeprefix("u/")
    sort = (request.args.get("sort") or "best").strip().lower()
    top_time = (request.args.get("top_time") or "all").strip().lower()
    after = (request.args.get("after") or "").strip() or None
    results_query = (request.args.get("results_query") or "").strip()
    over18 = request.args.get("over18") == "1"

    if top_time not in {"hour", "day", "week", "month", "year", "all"}:
        top_time = "all"

    if sort not in {value for value, _ in UI_SORT_OPTIONS}:
        sort = "best"

    session["over18"] = over18

    client = RedditClient(over18=over18)
    search_results: list[dict[str, Any]] = []
    user_results: list[dict[str, Any]] = []
    posts: list[dict[str, Any]] | None = None
    next_after: str | None = None
    subreddit_meta: dict[str, Any] | None = None
    user_meta: dict[str, Any] | None = None
    error: str | None = None
    active_view: str | None = None
    media_count = 0
    search_pages_fetched = 0
    search_limit_hit = False

    if username:
        active_view = "user"
    elif subreddit:
        active_view = "subreddit"

    api_sort = sort
    if active_view == "user":
        if sort == "best":
            api_sort = "new"
        elif sort == "rising":
            api_sort = "hot"

    sort_label_map = dict(UI_SORT_OPTIONS)
    current_sort_label = sort_label_map.get(sort, sort.capitalize())
    top_time_label_map = dict(TOP_TIME_OPTIONS)
    top_time_label = top_time_label_map.get(top_time, "All time")
    max_api_pages = MAX_API_PAGES_PER_SEARCH if results_query else MAX_API_PAGES_PER_VIEW
    search_sort = ui_sort_to_search_sort(sort)

    try:
        if query:
            search_results = client.search_subreddits(query)
        if user_query:
            user_results = client.search_users(user_query)

        if active_view == "subreddit" and subreddit:
            if results_query:
                fetch_page = lambda after=None, limit=API_BATCH_SIZE: client.search_subreddit_posts(
                    subreddit,
                    query=results_query,
                    after=after,
                    limit=limit,
                    sort=search_sort,
                    top_time=top_time,
                )
            else:
                fetch_page = lambda after=None, limit=API_BATCH_SIZE: client.load_subreddit(
                    subreddit,
                    sort=api_sort,
                    after=after,
                    limit=limit,
                    top_time=top_time,
                )

            posts, next_after, media_count, search_pages_fetched, search_limit_hit = collect_unique_posts(
                fetch_page,
                initial_after=after,
                target_media_items=DISPLAY_MEDIA_ITEMS_PER_PAGE,
                max_api_pages=max_api_pages,
            )
            subreddit_meta = client.load_subreddit_about(subreddit)

        if active_view == "user" and username:
            if results_query:
                fetch_page = lambda after=None, limit=API_BATCH_SIZE: client.search_user_posts(
                    username,
                    query=results_query,
                    after=after,
                    limit=limit,
                    sort=search_sort,
                    top_time=top_time,
                )
            else:
                fetch_page = lambda after=None, limit=API_BATCH_SIZE: client.load_user_submitted(
                    username,
                    sort=api_sort,
                    after=after,
                    limit=limit,
                    top_time=top_time,
                )

            posts, next_after, media_count, search_pages_fetched, search_limit_hit = collect_unique_posts(
                fetch_page,
                initial_after=after,
                target_media_items=DISPLAY_MEDIA_ITEMS_PER_PAGE,
                max_api_pages=max_api_pages,
            )
            user_meta = client.load_user_about(username)
    except Exception as exc:
        error = str(exc)

    return render_template_string(
        PAGE_TEMPLATE,
        title=APP_TITLE,
        query=query,
        subreddit=subreddit,
        user_query=user_query,
        username=username,
        sort=sort,
        api_sort=api_sort,
        top_time=top_time,
        sort_options=UI_SORT_OPTIONS,
        top_time_options=TOP_TIME_OPTIONS,
        top_time_label=top_time_label,
        current_sort_label=current_sort_label,
        over18=over18,
        results_query=results_query,
        search_results=search_results,
        user_results=user_results,
        posts=posts,
        next_after=next_after,
        subreddit_meta=subreddit_meta,
        user_meta=user_meta,
        media_count=media_count,
        search_pages_fetched=search_pages_fetched,
        search_limit_hit=search_limit_hit,
        active_view=active_view,
        error=error,
        media_download_url=media_download_url,
        build_download_filename=build_download_filename,
    )


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "65010"))
    app.run(host=host, port=port, debug=False)
