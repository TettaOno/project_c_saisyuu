/**
 * 画像ファイルをバックエンドのYOLOv8 APIに送信する。
 *
 * @param {File} file - アップロードする画像ファイルオブジェクト
 * @returns {Promise<object>} - サーバーから返されたJSONデータを含むPromise
 */
export function uploadImageToApi(file) {
    const formData = new FormData();
    // 🚨 Flask側 (services/routes.py) の request.files['file'] とキー名を合わせる
    formData.append('file', file);

    // Fetch APIでバックエンドAPIへPOSTリクエストを送信
    return fetch('/api/detect-disease', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            // HTTPエラーが発生した場合、詳細なエラーテキストを取得してPromiseを拒否する
            return response.text().then(text => {
                // Flask側でエラーが発生した場合のメッセージをキャッチしやすくする
                throw new Error(`HTTP Error! Status: ${response.status}. Detail: ${text}`);
            });
        }
        // 成功した場合、JSON形式で結果を解析して返す
        return response.json();
    });
    // .catch() は呼び出し元 (ui.js の uploadImage 関数) で処理されます
}