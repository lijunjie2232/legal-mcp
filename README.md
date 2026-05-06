# 日本法律MCPサーバー

[![Pythonバージョン](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![ライセンス](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-repository-black.svg)](https://github.com/lijunjie2232/legal-mcp)

[![English](https://img.shields.io/badge/English-US-blue.svg)](README_EN.md)
[![日本語](https://img.shields.io/badge/日本語-JA-blue.svg)](README.md)

Elasticsearchに保存された日本の法令文書を検索・探索するためのModel Context Protocol（MCP）サーバーです。このサーバーは、高度な機能（スマートハイライトや生JSONアクセスなど）を備えた日本の法律・条例の検索、取得、分析ツールを提供します。

## 機能

- 🔍 **日本法令検索**: マルチフィールドマッチングによる自然言語検索
- 📄 **全文書取得**: IDによる完全な法令詳細の取得とフォーマット出力
- 💾 **生JSONアクセス**: ネストされたフィールドを含む完全な生JSONデータ構造の取得
- 📊 **クラスタ監視**: Elasticsearchクラスタのヘルスチェックとステータス確認
- 🎯 **スマートハイライト**: 複数フィールドからの一致箇所をハイライトしたインテリジェントなスニペット抽出
- ⚡ **非同期サポート**: より良いパフォーマンスのための完全なasync/awaitサポート
- 🌐 **複数トランスポート**: stdio、SSE、ストリーミング可能HTTPトランスポートのサポート
- 📝 **設定可能なロギング**: コンソールおよびファイル出力オプションを備えたloguruベースのロギング

## インストール

### クイックインストール

`curl`または`wget`を使用してインストールスクリプトをダウンロードして実行：

```bash
# curlを使用
bash -c "$(curl -fsSL https://raw.githubusercontent.com/lijunjie2232/legal-mcp/refs/heads/master/install.sh)"
```

```bash
# wgetを使用
bash -c "$(wget https://raw.githubusercontent.com/lijunjie2232/legal-mcp/refs/heads/master/install.sh -O -)"
```

### ソースから

```bash
# リポジトリのクローン
git clone git@github.com:lijunjie2232/legal-mcp.git
cd legal-mcp

# 仮想環境の作成
python -m venv .venv
source .venv/bin/activate  # Windowsの場合: .venv\Scripts\activate

# 依存関係のインストール
pip install -e .
```

### uvの使用（推奨）

```bash
# uvがまだインストールされていない場合
curl -LsSf https://astral.sh/uv/install.sh | sh

# クローンしてインストール
git clone git@github.com:lijunjie2232/legal-mcp.git
cd legal-mcp
uv sync
```

## 設定

プロジェクトルートに`config.yaml`ファイルを作成：

```yaml
# Elasticsearch接続設定
es:
  host: "https://l2533584225-elasticsearch-legal-docs.hf.space"
  # port: 9200
  # scheme: "https"
  user: "llm_searcher"
  password: "llm_searcher"

# インデックス設定
index:
  name: "legal_documents"

# ログ設定
log:
  level: "INFO"
  # file: "/path/to/logfile.log"  # ファイルロギングを有効にする場合はコメントアウトを外す

```

設定システムはPydanticモデルを使用して検証を行い、YAMLファイルからの読み込みをサポートしています。設定ファイルが存在しない場合はデフォルト値が提供されます。

## 使用方法

### コマンドライン

```bash
# MCPサーバーの起動（デフォルト: stdioトランスポート）
legal-mcp

# 特定のトランスポートを指定
legal-mcp stdio              # 標準入出力（Claude Desktop用）
legal-mcp sse                # Server-Sent Events（Webベースクライアント用）
legal-mcp streamable-http    # HTTPストリーミング

# ヘルプを表示
legal-mcp --help
```

### Python API

```python
from legal_mcp import search_laws, get_law_by_id, get_raw_json_by_id, get_cluster_status
import asyncio

async def main():
    # フィルター付きで法令を検索
    results = await search_laws("憲法", era="Reiwa", law_type="Act", limit=5)
    print(results)

    # 完全な法令詳細を取得
    law = await get_law_by_id("419AC1000000051_20260521_504AC0000000048")
    print(law)

    # 生JSONデータを取得
    raw_data = await get_raw_json_by_id("419AC1000000051_20260521_504AC0000000048")
    print(raw_data)

    # クラスタステータスを確認
    status = await get_cluster_status()
    print(status)

asyncio.run(main())
```

### モジュールとして実行

```python
from legal_mcp.mcp_runner import run_mcp_server

# stdioトランスポートで実行（デフォルト）
run_mcp_server()

# またはSSEトランスポートで実行
run_mcp_server(transport="sse")
```

### 利用可能なツール

MCPサーバーは以下のツールを提供します：

1. **search_laws**: 日本の法律・条例を検索
   - パラメーター:
     - `query` (str): 検索語句（例: "憲法"、"税"、"データプライバシー"）
     - `era` (Optional[str]): 元号でフィルター（例: "Showa"、"Heisei"、"Reiwa"）
     - `law_type` (Optional[str]): 法令種別でフィルター（例: "Act"、"CabinetOrder"、"MinisterialOrdinance"）
     - `limit` (int): 返す結果の最大数（デフォルト: 5）
   - 戻り値: 法令ID、タイトル、法令番号、関連スニペットを含むフォーマット済み文字列
   - 機能: ハイライト付きのマルチフィールド検索、スマートスニペット抽出
2. **get_law_by_id**: IDによってフォーマットされた法令詳細を取得
   - パラメーター: `law_id` (str) - 法令の一意の識別子
   - 戻り値: メタデータと法的コンテンツを含むフォーマット済みmarkdownスタイル出力
   - 含まれる情報: 法令タイトル、番号、種別、元号、年、構造化されたコンテンツセクション
3. **get_raw_json_by_id**: IDによって完全な生JSONデータを取得
   - パラメーター: `law_id` (str) - 法令の一意の識別子
   - 戻り値: law_id、meta、raw_full_jsonを含む辞書
   - 注意: 一部の文書はサイズ制限のため生JSONが省略されている場合があります
4. **get_cluster_status**: Elasticsearchクラスタのヘルスチェック
   - パラメーター不要
   - 戻り値: ステータス、ノード数、文書数、インデックス名を含む辞書
   - 監視と診断に有用

### アーキテクチャ概要

プロジェクトはモジュラーアーキテクチャに従っています：

- **`mcp_config.py`**: YAMLサポートを備えたPydanticモデルを使用した設定管理
- **`mcp_util.py`**: ロガーセットアップとElasticsearchクライアント作成を含むユーティリティ関数
- **`mcp_server.py`**: コアMCPツール実装（検索、取得、クラスタステータス）
- **`mcp_runner.py`**: 複数トランスポートプロトコルをサポートするサーバーランナー
- **`__init__.py`**: シングルトン設定とクライアントセットアップを備えたモジュール初期化

主要なデザインパターン：

- 設定とElasticsearchクライアントのシングルトンパターン
- すべてのMCPツールの非同期/待機
- loguruによる構造化ロギング
- コードベース全体での型ヒント

## プロジェクト構造

```
legal-mcp/
├── legal_mcp/              # メインパッケージ
│   ├── __init__.py         # パッケージ初期化、シングルトン設定とクライアント
│   ├── mcp_config.py       # Pydantic設定モデル
│   ├── mcp_util.py         # ロガーセットアップとESクライアントユーティリティ
│   ├── mcp_server.py       # MCPツール実装（4つのツール）
│   └── mcp_runner.py       # 複数トランスポートサポートを備えたサーバーランナー
├── pytests/                # テストスイート
│   ├── conftest.py         # テストフィクスチャと設定
│   ├── test_config.py      # 設定テスト
│   ├── test_search.py      # 検索機能テスト
│   ├── test_retrieval.py   # 文書取得テスト
│   └── test_cluster.py     # クラスタステータステスト
├── data/                   # 法令文書データ（JSON/XML）
├── es_data/                # Elasticsearchデータディレクトリ
├── script/                 # ユーティリティスクリプト
│   ├── es_import.py        # Elasticsearchインポートスクリプト
│   ├── xml_to_json.py      # XMLからJSONへの変換
│   └── schema_extractor.py # スキーマ抽出ユーティリティ
├── config.yaml             # YAML設定ファイル
├── config.example.yaml     # 設定テンプレート例
├── pyproject.toml          # プロジェクトメタデータと依存関係
├── run_server.py           # 代替サーバーエントリーポイント
└── README.md               # このファイル
```

## 要件

- Python 3.14+
- Elasticsearch 9.3+（適切なインデックスマッピングが設定されていること）
- 仮想環境（推奨）
- Elasticsearchインデックス内の日本法令文書

## Elasticsearchインスタンス

> ⚠️ **注意**: 法令文書ElasticsearchインスタンスのデモAPIは [https://l2533584225-elasticsearch-legal-docs.hf.space](https://huggingface.co/spaces/l2533584225/elasticsearch-legal-docs) で利用可能です。30分間非アクティブ状態が続くとスリープ状態になる可能性があるため、使用前にアクティブ化するか、独自のElasticsearchインスタンスを構築してください。

### プライベートElasticsearchインスタンスの作成

独自のElasticsearchインスタンスを作成するには、いくつかのオプションがあります：

1. **Hugging Face上**（無料ティアを使用）: スペースを作成し、[Dockerfile](https://huggingface.co/spaces/l2533584225/elasticsearch-legal-docs/raw/main/Dockerfile)（現在のHFデモと同じ）をアップロードします。

2. **プライベートサーバー上**:
   ```bash
   wget https://huggingface.co/spaces/l2533584225/elasticsearch-legal-docs/raw/main/Dockerfile
   docker build -t elasticsearch-legal-docs:dev .
   docker run -d -p 9200:9200 -p 9300:9300 --name elasticsearch-legal-docs elasticsearch-legal-docs:dev
   ```
   DockerでElasticsearchを実行する他のオプションについては、[公式ドキュメント](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-docker-basic)を参照してください。

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています - 詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 謝辞

- 法令文書データは [e-Gov 法令検索](https://laws.e-gov.go.jp/) から提供
- [Model Context Protocol](https://modelcontextprotocol.io/) で構築
- [Elasticsearch](https://www.elastic.co/elasticsearch/) で動作
- MCPサーバー実装には [FastMCP](https://github.com/jlowin/fastmcp) を使用
- 日本法令文書データ構造と検索最適化

## トラブルシューティング

### よくある問題

1. **Elasticsearchへの接続が拒否される**
   - Elasticsearchが実行中か確認: `curl http://localhost:9200`
   - `config.yaml`の認証情報を確認
   - インデックスが存在し、文書が含まれていることを確認

2. **検索結果が見つからない**
   - インデックス名がElasticsearch設定と一致しているか確認
   - 文書が適切にインデックスされているか確認
   - より広い検索語句を試す

3. **インポートエラー**
   - 仮想環境がアクティブ化されていることを確認
   - `pip install -e .` を実行して開発モードでインストール
   - Pythonバージョンを確認（3.14+が必要）

4. **ロギングが機能しない**
   - `config.yaml`のログレベルを確認
   - ファイルロギングを使用する場合、ファイル権限を確認
   - コンソールロギングはデフォルトで有効
