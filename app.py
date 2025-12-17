import streamlit as st
import requests
import pandas as pd
from io import BytesIO, StringIO 
import re
import time

# --- 定数設定 ---
# APIのエンドポイント
API_URL = "https://www.showroom-live.com/api/event/room_list"
# オーガナイザーリストのURL
ORGANIZER_LIST_URL = "https://mksoul-pro.com/showroom/file/organizer_list.csv"

# --- 関数: APIから全ページデータを取得 ---
@st.cache_data(show_spinner="イベント参加ルーム情報を取得中...")
def fetch_all_room_data(event_id):
    """
    指定されたイベントIDの全ページからルーム情報を取得し、
    ルームID、イベントID、ルーム名、オーガナイザーIDのリストを返します。
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

            # データを処理して、必要な情報を抽出 (room_id, event_id, organizer_id, room_name)
            for room_data in room_list:
                room_id = room_data.get("room_id")
                room_name = room_data.get("room_name", "") # ルーム名
                organizer_id = room_data.get("organizer_id", 0) # オーガナイザーID
                
                # event_entryネスト内のevent_idを取得
                entry_data = room_data.get("event_entry", {})
                current_event_id = entry_data.get("event_id")

                if room_id and current_event_id:
                    # 全て文字列に統一
                    all_rooms.append({
                        "room_id": str(room_id),
                        "event_id": str(current_event_id),
                        "room_name": str(room_name),
                        "organizer_id": str(organizer_id),
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

# --- 関数: オーガナイザーリストを取得し、ID-Nameの辞書を作成 ---
@st.cache_data(show_spinner="オーガナイザーリストを取得中...")
def fetch_organizer_list(url):
    """
    指定されたURLからCSVファイルをダウンロードし、オーガナイザーIDをキー、
    オーガナイザー名を値とする辞書を返します。
    """
    st.info(f"オーガナイザーリストを **{url}** から取得します。")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # CSVデータをStringIOで読み込む
        # CSVは通常、UTF-8で提供されると仮定
        csv_data = StringIO(response.content.decode('utf-8'))
        
        # 1行目をヘッダーとして読み込み、2列を文字列として取得
        df = pd.read_csv(csv_data, header=0, dtype=str)
        
        # 辞書を作成 {オーガナイザーID: オーガナイザー名}
        # 列名が日本語なので、存在チェック
        if len(df.columns) >= 2:
            # 1列目がID、2列目が名前として使用
            organizer_map = pd.Series(df.iloc[:, 1].values, index=df.iloc[:, 0]).to_dict()
            st.success(f"オーガナイザーリストを正常に取得しました。**{len(organizer_map)}** 件")
            return organizer_map
        else:
            st.error("オーガナイザーリストのCSVファイルにIDと名前の列が見つかりません。")
            return {}

    except requests.exceptions.RequestException as e:
        st.error(f"オーガナイザーリストのダウンロード中にエラーが発生しました: {e}")
        return {}
    except Exception as e:
        st.error(f"オーガナイザーリストの処理中に予期せぬエラーが発生しました: {e}")
        return {}

# --- メイン Streamlit アプリケーション ---
def main():
    st.title("SHOWROOM イベント参加ルーム情報 抽出ツール")
    st.markdown("---")

    # --- 0. オーガナイザーリストの取得 ---
    organizer_map = fetch_organizer_list(ORGANIZER_LIST_URL)
    
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
    if st.button("🚀 実行: ルーム情報を取得"):
        
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
        
        # --- 3. オーガナイザー名マッピング処理 ---
        st.subheader("🔗 オーガナイザー名のマッピング")
        if organizer_map:
            # organizer_idに基づいてorganizer_nameをマッピング
            # マッチしない場合はNaNになるため、fillna('')でブランクに変換
            new_df['organizer_name'] = new_df['organizer_id'].map(organizer_map).fillna('')
            st.success("オーガナイザー名のマッピングを完了しました。")
        else:
            new_df['organizer_name'] = ''
            st.warning("オーガナイザーリストが取得できなかったため、オーガナイザー名はブランクのままです。")

        # --- 4. 重複処理ロジック ---
        st.markdown("---")
        st.header("🔄 重複排除・ソート")

        final_df = new_df.copy()

        # 1. event_idを数値に変換（比較のため）
        final_df['event_id_num'] = pd.to_numeric(final_df['event_id'], errors='coerce')
        
        # 2. room_idでグルーピングし、event_id_numの最大値（新しいもの）を持つ行を選択
        final_df = final_df.loc[
            final_df.groupby('room_id')['event_id_num'].idxmax()
        ]
        
        # 3. 作業用列を削除し、最終的な列の順番を設定
        final_df = final_df.drop(columns=['event_id_num'])
        
        # 💡 修正箇所: room_idを数値に変換してからソートする
        final_df['room_id_num'] = pd.to_numeric(final_df['room_id'], errors='coerce')
        final_df = final_df.sort_values(by='room_id_num', ascending=True)
        final_df = final_df.drop(columns=['room_id_num']) # 作業用列を削除

        # 最終的な出力列の順番
        OUTPUT_COLUMNS = ['room_id', 'event_id', 'room_name', 'organizer_id', 'organizer_name']
        final_df = final_df[OUTPUT_COLUMNS]

        st.subheader("📊 最終的な結果データ（重複排除・ソート後）")
        st.dataframe(final_df)
        st.success(f"重複排除・ソート後、**{len(final_df)}** 件のユニークなルーム情報が確定しました。")
        
        # --- 5. CSVダウンロード機能 ---
        # DataFrameをCSV文字列（UTF-8）に変換（ヘッダーなし）
        # NOTE: Windows環境で文字化けしないよう、Shift_JIS (CP932) に変換する
        csv_string_utf8 = final_df.to_csv(index=False, header=False, encoding='utf-8')
        
        # 文字列をCP932（Shift_JIS）バイトデータに変換
        # BOM付きUTF-8も選択肢だが、汎用的なShift_JIS系で対応
        csv_data_cp932 = csv_string_utf8.encode('cp932', 'ignore') 
        
        st.download_button(
            label="⬇️ 結果をCSVファイルとしてダウンロード",
            data=csv_data_cp932, # CP932バイトデータを渡す
            file_name='showroom_event_liver_info.csv', # ファイル名を更新
            mime='text/csv',
            key='download-csv'
        )
        
if __name__ == "__main__":
    main()