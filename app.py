import streamlit as st
import requests
import pandas as pd
# from ftplib import FTP # 削除
from io import BytesIO # BytesIOは後続のCSVダウンロードボタンのために残します
import re
import time

# --- 定数設定 ---
# APIのエンドポイント
API_URL = "https://www.showroom-live.com/api/event/room_list"
# FTPアップロード先のファイル名とパス (削除)
# FTP_FILE_PATH = "/mksoul-pro.com/showroom/file/event_liver_list.csv"

# --- 関数: APIから全ページデータを取得 ---
@st.cache_data(show_spinner="イベント参加ルーム情報を取得中...")
def fetch_all_room_data(event_id):
    """
    指定されたイベントIDの全ページからルーム情報を取得し、
    ルームIDとイベントIDのリストを返します。
    """
    st.write(f"イベントID: **{event_id}** の情報を取得します。")
    all_rooms = []
    page = 1
    
    # ページング処理を無限ループで行い、データがなくなるまで続ける
    while True:
        try:
            # API URLを構築
            url = f"{API_URL}?event_id={event_id}&p={page}"
            
            # APIコール
            response = requests.get(url, timeout=10)
            response.raise_for_status() # HTTPエラーが発生した場合に例外を発生させる
            data = response.json()

            # ルームリストを抽出
            room_list = data.get("list", [])
            
            if not room_list:
                # リストが空であれば、最終ページに到達したと判断してループを終了
                st.info(f"ページ {page}: ルームが見つかりませんでした。全 {page-1} ページを処理しました。")
                break

            # データを処理して、ルームIDとイベントIDのペアを抽出
            for room_data in room_list:
                # room_idはトップレベルまたはevent_entryネスト内にあります。
                # どちらも同じ情報であるため、トップレベルのものを採用します。
                room_id = room_data.get("room_id")
                # event_entryネスト内のevent_idを取得
                entry_data = room_data.get("event_entry", {})
                current_event_id = entry_data.get("event_id")

                if room_id and current_event_id:
                    # room_idは文字列型と数値型が混在している可能性があるため、文字列に統一
                    all_rooms.append({
                        "room_id": str(room_id),
                        "event_id": str(current_event_id)
                    })
            
            # APIのレスポンスから次のページ番号を取得
            next_page = data.get("next_page")
            st.text(f"ページ {page} 処理完了。次ページ: {next_page}")

            if next_page is None or next_page == page:
                # next_pageが存在しないか、現在のページと同じ場合はループ終了
                break

            page = next_page
            # サーバー負荷軽減のため、ページ間に短い待機時間を設ける
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            st.error(f"APIリクエストエラー (ページ {page}): {e}")
            break
        except Exception as e:
            st.error(f"予期せぬエラーが発生しました (ページ {page}): {e}")
            break

    return all_rooms

# --- 関数: FTPからファイルをダウンロード (削除) ---
# def download_ftp_file(ftp, remote_path):
#     """FTPサーバーから既存のCSVファイルをダウンロードし、Pandas DataFrameとして返します。"""
#     ... (削除)

# --- 関数: DataFrameをFTPにアップロード (削除) ---
# def upload_ftp_file(ftp, df, remote_path):
#     """DataFrameをCSV形式でFTPサーバーにアップロードします。（バイトデータとして転送）"""
#     ... (削除)

# --- メイン Streamlit アプリケーション ---
def main():
    st.title("SHOWROOM イベント参加ルームID 抽出ツール")
    st.markdown("---")
    
    # --- 1. イベントID入力 ---
    event_ids_input = st.text_area(
        "📝 イベントIDを入力してください (複数可。改行またはカンマ区切り):",
        help="例: 40883, 40884\nまたは\n40883\n40884"
    )
    
    # 複数のイベントIDを解析
    event_ids = []
    if event_ids_input:
        # 改行またはカンマで分割し、不要な空白を除去
        raw_ids = re.split(r'[\n,]+', event_ids_input.strip())
        # 空でない、数字のみの文字列を抽出
        event_ids = [eid.strip() for eid in raw_ids if eid.strip().isdigit()]

    if not event_ids:
        st.warning("イベントIDを入力してください。")
        return

    st.info(f"処理対象のイベントID: **{', '.join(event_ids)}**")
    st.markdown("---")

    # --- 2. 実行ボタン ---
    if st.button("🚀 実行: ルームIDを取得"):
        
        # 全イベントのデータ取得
        new_data_list = []
        with st.spinner("APIからデータを取得中..."):
            for event_id in event_ids:
                rooms = fetch_all_room_data(event_id)
                new_data_list.extend(rooms)
        
        if not new_data_list:
            st.error("入力された全てのイベントIDについて、ルーム情報を取得できませんでした。処理を中断します。")
            return
            
        # 取得データをDataFrameに変換
        new_df = pd.DataFrame(new_data_list, dtype=str)
        # 列の順番を要件通りに [room_id, event_id] に設定
        new_df = new_df[['room_id', 'event_id']]
        st.subheader("✅ 取得した新規データ")
        st.dataframe(new_df)
        st.success(f"全イベントから合計 **{len(new_df)}** 件のルームIDを取得しました。")
        
        # --- 3. データ処理と重複排除 ---
        st.markdown("---")
        st.header("🔄 データ結合・重複排除・結果表示")
        
        # ここでは既存ファイルがないため、new_df自体が最終データとなる（結合処理が不要）
        
        # --- 4. 重複処理ロジック ---
        # 結合処理がなくなったため、取得したnew_df内での重複排除を行う。
        # ただし、fetch_all_room_dataの性質上、通常はnew_df内に同一room_idの重複はないが、
        # 複数のevent_idが入力された場合に備え、room_idとevent_idのセットで重複を排除する
        # (ここでは既存のロジックに近くなるように、room_idをキーにevent_id_numが新しいものを残すロジックを採用する)
        
        final_df = new_df.copy() # 新規データのみを処理対象とする
        
        # 1. event_idを数値に変換（比較のため）
        final_df['event_id_num'] = pd.to_numeric(final_df['event_id'], errors='coerce')
        
        # 2. room_idでグルーピングし、event_id_numの最大値（新しいもの）を持つ行を選択
        #    - room_idが同じ場合は、event_idが大きい方（新しいイベント）のエントリを残す。
        final_df = final_df.loc[
            final_df.groupby('room_id')['event_id_num'].idxmax()
        ]
        
        # 3. 作業用列を削除し、最終的な形式に整える
        final_df = final_df[['room_id', 'event_id']]
        
        # 💡 修正箇所: room_idを数値に変換してからソートする
        final_df['room_id_num'] = pd.to_numeric(final_df['room_id'], errors='coerce')
        final_df = final_df.sort_values(by='room_id_num', ascending=True)
        final_df = final_df.drop(columns=['room_id_num']) # 作業用列を削除

        st.subheader("📊 最終的な結果データ（重複排除・ソート後）")
        st.dataframe(final_df)
        st.success(f"重複排除・ソート後、**{len(final_df)}** 件のユニークなルームIDが確定しました。")
        
        # --- 5. CSVダウンロード機能を追加 ---
        # DataFrameをCSVバイトデータに変換
        csv_data = final_df.to_csv(index=False, header=False, encoding='utf-8')
        
        st.download_button(
            label="⬇️ 結果をCSVファイルとしてダウンロード",
            data=csv_data.encode('utf-8'),
            file_name='showroom_event_liver_list.csv',
            mime='text/csv',
            key='download-csv'
        )
        
if __name__ == "__main__":
    main()