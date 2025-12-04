import os
from flask import Flask, render_template, request, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
import uuid # uuidモジュールを追加

# 修正: 絶対インポートに戻し、flask run で実行することで解決を図る
from services.routes import api_bp 
from services.ai_service import load_models, run_detection_and_analyze # AIモデルの初期ロード関数と推論関数をインポート

# --- 設定 ---
# UPLOAD_FOLDERは routes.py 側で定義されるが、ここでは省略
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads')) # 新たに追加、あるいは既存のものを修正

# Flaskアプリケーションの初期化
app = Flask(__name__)

# --- AIモデルの初期ロード ---
# サーバー起動時に、モデルをメモリにロードする
try:
    load_models() 
except ConnectionError as e:
    # モデルロード失敗は致命的なので、ログに出力
    print(f"致命的エラー: {e}")
    # アプリケーションは起動するが、APIリクエストはエラーを返すようになる

# --- ファイル監視ロジック ---
IMG_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'img')) # 絶対パスで指定

class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        print(f"DEBUG: on_createdイベントがトリガーされました: {event.src_path}, is_directory: {event.is_directory}")
        if not event.is_directory and event.src_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            # ファイルが完全に書き込まれるのを待つために数秒待機
            time.sleep(3) # 2秒から3秒に延長
            print(f"新しくファイルが追加されました: {event.src_path}")
            try:
                import shutil # ファイルコピーのために追加

                result_disease, result_confidence, all_detections, drawn_img_data, original_filename = run_detection_and_analyze(event.src_path)
                print(f"推論結果概要: {result_disease}, 確信度: {result_confidence}, 総検出数: {len(all_detections)}")

                if all_detections: # 検出結果がある場合 (フィルタリング後)
                    print("--- 各学習データからの推論結果詳細 ---")
                    # 判定率0.75以上の検出結果のみをフィルタリング
                    filtered_detections = [d for d in all_detections if d['confidence'] >= 0.75]

                    if filtered_detections: # フィルタリング後に検出結果がある場合のみ処理
                        for i, detection in enumerate(filtered_detections):
                            print(f"  検出 {i+1}: (モデル: {detection['model_filename']})") # モデルファイル名も表示
                            print(f"    病気/害虫: {detection['disease']}")
                            print(f"    確信度: {detection['confidence']}")
                            print(f"    モデルカテゴリ: {detection['model_category']}")
                            print(f"    バウンディングボックス: x_min={detection['box']['x_min']}, y_min={detection['box']['y_min']}, x_max={detection['box']['x_max']}, y_max={detection['box']['y_max']}")
                        print("----------------------")

                        # 検出されたすべての物体に対して画像を保存するように変更
                        # 一時フォルダを経由せず、直接resultフォルダに保存
                        unique_output_filename = f"detected_{uuid.uuid4()}_{original_filename}"
                        
                        for detection in filtered_detections:
                            model_category = detection['model_category']
                            # model_filename = detection['model_filename'] # 不要になったので削除

                            # モデルファイル名から拡張子を除いた部分をフォルダ名にする (これは不要)
                            # model_base_name = os.path.splitext(model_filename)[0]

                            # 保存先パスのベースディレクトリを修正
                            BASE_RESULT_DIR = os.path.join(
                                os.path.dirname(os.path.abspath(__file__)), 
                                'result' 
                            )

                            # 保存先パスの構築: result/カテゴリ/
                            save_dir = os.path.join(
                                BASE_RESULT_DIR, model_category
                            )
                            os.makedirs(save_dir, exist_ok=True)
                            
                            # 描画された画像データを直接resultフォルダに保存
                            try:
                                import cv2 # cv2をインポート
                                output_filepath = os.path.join(save_dir, unique_output_filename)
                                cv2.imwrite(output_filepath, drawn_img_data)
                                print(f"✅ 推論画像をresultフォルダに直接保存しました: {output_filepath} (カテゴリ: {model_category})")
                            except PermissionError:
                                print(f"❌ ファイル保存エラー: {save_dir} への書き込み権限がありません。")
                            except Exception as save_e:
                                print(f"❌ ファイル保存中に予期せぬエラーが発生しました: {save_e}")
                            
                            time.sleep(0.5) # 保存後に少し遅延を設ける
                    else:
                        print("💡 判定率0.75以上の検出結果がないため、画像を保存しませんでした。")
                else:
                    print("💡 検出結果がないため、画像を保存しませんでした。")

            except Exception as e:
                print(f"推論中にエラーが発生しました: {e}")
            finally:
                # 推論処理が完了したら、元の画像をimgフォルダから削除
                if os.path.exists(event.src_path):
                    os.remove(event.src_path)
                    print(f"元の画像ファイル '{event.src_path}' をimgフォルダから削除しました。")
                # 一時フォルダ内の画像も削除 (このロジックは不要になるので削除)
                # if os.path.exists(temp_output_path):
                #     os.remove(temp_output_path)
                #     print(f"一時推論結果ファイル '{temp_output_path}' を削除しました。")

    def on_moved(self, event):
        print(f"DEBUG: on_movedイベントがトリガーされました: From {event.src_path} to {event.dest_path}, is_directory: {event.is_directory}")

    def on_deleted(self, event):
        print(f"DEBUG: on_deletedイベントがトリガーされました: {event.src_path}, is_directory: {event.is_directory}")

    def on_modified(self, event):
        print(f"DEBUG: on_modifiedイベントがトリガーされました: {event.src_path}, is_directory: {event.is_directory}")

def start_file_watcher():
    if not os.path.exists(IMG_FOLDER):
        os.makedirs(IMG_FOLDER) # imgフォルダが存在しない場合は作成
        
    event_handler = ImageHandler()
    observer = Observer()
    observer.schedule(event_handler, IMG_FOLDER, recursive=False)
    observer.start()
    print(f"--- ファイル監視を開始しました: {IMG_FOLDER} ---") # 監視パスを表示
    try:
        while True:
            time.sleep(1) # 1秒ごとに監視をチェック
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# --- ルーティングの登録 ---
# services/routes.py で定義された Blueprint を登録し、/api/ のプレフィックスを付ける
# app.register_blueprint(api_bp, url_prefix='/api') 

# --- 静的ページのルート ---
@app.route('/')
def index():
    # templatesフォルダ内の index.html を読み込んで表示
    return render_template('index.html')

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "ファイルが添付されていません"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "ファイル名が空です"}), 400
    
    original_filename = file.filename
    # ユニークなファイル名を生成し、IMG_FOLDERに保存
    unique_filename = f"webcam_capture_{uuid.uuid4()}_{original_filename}"
    filepath = os.path.join(IMG_FOLDER, unique_filename)
    
    try:
        file.save(filepath)
        print(f"画像ファイル '{original_filename}' をIMG_FOLDERに保存しました: {filepath}")
        return jsonify({"message": "画像を正常にアップロードしました", "filename": unique_filename}), 200
    except Exception as e:
        print(f"ファイル保存エラー: {e}")
        return jsonify({"error": f"サーバー側でファイル保存に失敗しました: {e}"}), 500

if __name__ == '__main__':
    # ファイル監視を別スレッドで開始
    watcher_thread = threading.Thread(target=start_file_watcher)
    watcher_thread.daemon = True # メインスレッドが終了したら、監視スレッドも終了する
    watcher_thread.start()
    
    # 開発サーバーの起動
    # ファイル監視とFlaskのリローダーの競合を避けるため、use_reloader=Falseを設定
    app.run(debug=True, use_reloader=False)