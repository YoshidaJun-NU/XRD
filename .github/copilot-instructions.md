# Copilot / AI Agent Instructions — XRD Analysis Web App

目的: このリポジトリはスタンドアロンの Streamlit アプリ群（XRD解析）です。AIエージェントは次項を守り、修正や機能追加を進めてください。

## 主要ファイルとエントリポイント
- `XRD2.py` — 現在の**最も機能豊富な**メインアプリ（推奨の起動対象）。
- `XRD.py` — 簡易版の XRD 可視化ツール（軽い変更や参照に利用）。
- `Bragg.py` — ブラッグの法則の小さなユーティリティ（計算用）。
- `test` — スクリプト系の別バージョン（自動テストではなく、手動実行用の別実装）。
- `requirements.txt` — 必要パッケージ（streamlit, scipy, plotly, numpy, pandas）。
- `.devcontainer/devcontainer.json` — 開発コンテナ（Python 3.11、アタッチ時に `streamlit run XRD2.py` を実行する設定あり）。

## すぐに使うコマンド（開発者向け）
- ローカル環境構築:
  - python 仮想環境を作成して `pip install -r requirements.txt` を実行
- 起動（ローカル）:
  - `streamlit run XRD2.py` （オプション: `--server.enableCORS false --server.enableXsrfProtection false`）
- devcontainer: `.devcontainer` があるので Codespaces/VS Code の devcontainer 起動で自動的に `XRD2.py` を実行し、ポート 8501 を公開します。

## データ入出力の慣習（重要）
- 入力: CSV または TXT（拡張子 .csv, .txt を受け付ける）。
  - サイドバーでヘッダー行数をスキップ可能。
  - 列はユーザーが選択（デフォルトは列 0 = 2Theta, 列 1 = Intensity）。
  - TXT の場合は `pd.read_csv(..., sep=None, engine='python')` で自動判定して読み込む実装を採用している点に注意。
- 出力（UI）: Plotly 図、`st.data_editor` によるピーク選択テーブル（列名は以下を使用）
  - テーブル列: `Select`, `2Theta`, `d-value`, `Intensity`（**これらの名前を変更するとUIとの連携が壊れます**）。

## 解析パターン・重要な関数（すぐ参照するべき場所）
- d 値計算: `theta_to_d(two_theta)`（ファイル頭にある `WAVELENGTH` 定数を利用）
- 格子理論位置: `get_theoretical_ratios(lattice_type)` — 文字列は `"Lamellar"`, `"Hexagonal (Columnar)"`, `"Tetragonal (Columnar)"` を想定
- ピーク検出: `scipy.signal.find_peaks` を使い、UI 上で `prominence` と `width` を調整する設計。
- Reciprocal / Q-plot ロジックは `XRD2.py` にあり、
  - a*, b* = 1/a, 1/b の計算、
  - Q (observed) = 1/d、
  - Oblique では実空間 γ に対して逆空間 γ* = 180° - γ の計算を使用している点が重要。

## 変更時の注意点（守るべきルール）
- UI 表示テキストとラベルは日本語で統一されています。UI 文言を変更する場合は日本語の整合性を保ってください。
- `st.data_editor` で扱うカラム名や `analysis_type` の選択肢（文字列）はコード中で直接比較されています。文字列を変更する場合は全検索して安全に更新してください。
- 重い計算を導入する場合は Streamlit の非同期/キャッシュ（例: `st.cache_data` / `st.cache_resource`）を検討し、UI を固めないようにしてください。
- 既存の単一ファイル構成を大きく変えるリファクタは慎重に。まずは小さく、機能単位で分割し、手動で起動確認を行ってください。

## 既存のワークフローと期待されるレビュー手順
- 小さな修正（UI文言/バグ修正/軽微な機能追加）→ ローカルで `streamlit run XRD2.py` して動作確認→ PR を作成。
- 大きな設計変更（新しい依存, 非同期処理, パフォーマンス改善）→ 事前にイシューを立て、設計案を確認した上で分割コミットで実装。

---

必要なら、このファイルに具体的な PR チェックリストや追加のコード例（ユニットテスト導入の骨子など）を追記します。どの部分をもう少し詳しく書きますか？