document.addEventListener('DOMContentLoaded', () => {
    console.log("DOMContentLoadedイベント発火");
    const webcamVideo = document.getElementById('webcam-video');
    const captureCanvas = document.getElementById('capture-canvas');
    // const capturedImage = document.getElementById('captured-image'); // プレビューがないので不要
    // const captureButton = document.getElementById('capture-button'); // ボタンがないので不要

    let currentStream; // カメラのストリームを保持
    // let capturedBlob;  // キャプチャした画像データを保持 (ウェブカメラ用) // 撮影機能がないので不要
    let autoCaptureIntervalId; // 自動撮影のインターバルIDを保持

    // 1. ウェブカメラの起動
    async function startWebcam() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            webcamVideo.srcObject = stream; // 非表示だが、ここでストリームを割り当てる
            currentStream = stream; // ストリームを保存
            console.log('ウェブカメラが起動しました。');
        } catch (error) {
            console.error('ウェブカメラの起動に失敗しました:', error);
            alert('ウェブカメラの起動に失敗しました。カメラが接続されているか、ブラウザのアクセス許可を確認してください。');
        }
    }

    // 撮影し、サーバーに送信する関数
    function captureAndUploadImage() {
        if (!currentStream) {
            console.log('ウェブカメラが起動していません。スキップします。');
            return;
        }

        const context = captureCanvas.getContext('2d');
        captureCanvas.width = webcamVideo.videoWidth;
        captureCanvas.height = webcamVideo.videoHeight;
        context.drawImage(webcamVideo, 0, 0, captureCanvas.width, captureCanvas.height);

        captureCanvas.toBlob(async (blob) => {
            const filename = `webcam_capture_${new Date().toISOString().replace(/[:.]/g, '-')}.jpg`;
            const formData = new FormData();
            formData.append('file', blob, filename);

            try {
                const response = await fetch('/upload-image', {
                    method: 'POST',
                    body: formData,
                });

                const data = await response.json();
                if (response.ok) {
                    console.log('画像をサーバーにアップロードしました:', data.filename);
                } else {
                    console.error('画像アップロードエラー:', data.error);
                }
            } catch (error) {
                console.error('画像アップロード中にエラーが発生しました:', error);
            }
        }, 'image/jpeg', 0.9);
    }

    // ページロード時にウェブカメラを起動
    console.log("startWebcamを呼び出し");
    startWebcam().then(() => {
        // ウェブカメラが正常に起動したら、2分ごとに自動で写真を撮影してアップロードする
        autoCaptureIntervalId = setInterval(() => {
            if (currentStream) { // カメラがアクティブな場合のみ実行
                console.log("2分ごとの自動キャプチャとアップロードを開始します。");
                captureAndUploadImage();
            } else {
                console.log("ウェブカメラがアクティブではないため、自動キャプチャはスキップされます。");
            }
        }, 120 * 1000); // 2分 (120秒) ごと
        console.log("自動撮影インターバルを開始しました。ID:", autoCaptureIntervalId);
    });
});