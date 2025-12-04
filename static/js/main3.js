/**
 * main.js: アプリケーションのエントリポイント (起動処理)
 * * HTML要素の初期化、モジュールのインポートと接続、イベントリスナーの設定を行う。
 */

// 他のモジュールから必要な関数をインポート
import { ui } from './ui.js';
import { uploadImageToApi } from './api.js';
import { drawBoxes } from './canvas.js';


document.addEventListener('DOMContentLoaded', () => {

    // 1. HTML要素の取得（共有変数として利用）
    const fileInput = document.getElementById('tomatoImage');
    const detectButton = document.getElementById('detectButton');
    const previewImage = document.getElementById('preview');
    const resultElement = document.getElementById('result');
    const canvas = document.getElementById('detectionCanvas');
    const ctx = canvas ? canvas.getContext('2d') : null; 

    // 必須要素の存在チェック
    if (!fileInput || !detectButton || !previewImage || !resultElement || !canvas) {
        console.error("致命的エラー: 必要なHTML要素の一部が見つかりません。HTMLのIDを確認してください。");
        return;
    }

    // 2. 共有要素のパッケージング
    // 他のモジュールがDOM要素やインポートされた関数を参照できるように渡す
    const sharedElements = {
        fileInput,
        detectButton,
        previewImage,
        resultElement,
        canvas,
        ctx,
        uploadImageToApi, // api.jsの関数
        drawBoxes         // canvas.jsの関数
    };
    
    // 3. UIモジュールの初期化とイベントハンドラの取得
    const { previewFile, uploadImage } = ui(sharedElements);
    
    // 4. グローバルスコープに関数を公開（HTMLのインラインイベントから呼び出せるようにする）
    // NOTE: HTMLの onchange="previewFile()" や onclick="uploadImage()" に対応
    window.previewFile = previewFile;
    window.uploadImage = uploadImage;

    // 5. 初期状態の設定
    resultElement.innerHTML = "ファイルを選択してください。";

    console.log("モジュール化が成功し、アプリが起動しました。");
});