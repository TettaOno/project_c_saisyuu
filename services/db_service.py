import pymysql.cursors
from typing import Tuple, Any, Dict, List, Optional
import datetime

# --- データベース接続設定 ---
# 🚨 接続検証用のため、ダミーの設定が入っています。
# 実際に接続する際は、チームメンバーから正しい情報を取得して書き換えてください。
DB_CONFIG: Dict[str, Any] = {
    'host': '127.0.0.1',            # DBサーバーのIPアドレス (仮)
    'user': 'db_user',              # データベースユーザー名 (仮)
    'password': 'db_password',      # パスワード (仮)
    'db': 'tomato_disease_db',      # データベース名 (仮)
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def insert_detection_log(
    filename: str, 
    final_disease: str, 
    confidence: float, 
    detections: List[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    YOLOv8の検出結果をデータベースに挿入します。
    
    Args:
        filename: アップロードされた画像ファイル名。
        final_disease: 最も確信度の高い病名（代表結果）。
        confidence: 最も確信度の高い確信度。
        detections: YOLOv8からのすべての検出結果リスト（JSON文字列として保存）。
        
    Returns:
        Tuple[bool, str]: 成功/失敗を示すブール値とメッセージ。
    """
    import json
    
    try:
        # DB接続を試みる
        connection = pymysql.connect(**DB_CONFIG)
        
        # 検出結果リストをJSON文字列に変換
        detections_json = json.dumps(detections)

        with connection.cursor() as cursor:
            # データベースのテーブル名とカラムは仮定しています
            sql = """
            INSERT INTO detection_logs 
                (image_file, main_disease, confidence, detections_data, detection_time) 
            VALUES 
                (%s, %s, %s, %s, NOW())
            """
            
            # SQLインジェクションを防ぐため、データを%sで安全に渡します
            cursor.execute(sql, (filename, final_disease, confidence, detections_json))

        # コミットして変更を永続化
        connection.commit()
        connection.close()
        
        return True, "DB挿入処理が正常に実行されました。"
    
    except pymysql.err.OperationalError as e:
        # 接続拒否やDBが見つからないなど、接続設定の問題
        error_message = f"DB接続エラーが発生しました。 (設定: {DB_CONFIG['host']} / Error: {e.args[1]})"
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {error_message}")
        return False, error_message
    
    except Exception as e:
        # その他のエラー (例: テーブルが存在しない、JSON変換失敗など)
        error_message = f"DB処理中の予期せぬエラー: {e}"
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {error_message}")
        return False, error_message