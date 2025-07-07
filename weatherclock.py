"""
天気予報と時刻を表示する Tkinter アプリケーション

天気予報は OpenWeatherMap の API を使用し、時刻はシステムの現在時刻を表示

"""

import tkinter.ttk as ttk
import os 
import requests
import json
import math
import time
import sys
import vlc
import re
import jpholiday # 祝日判定用
import ctypes # スリープ制御用
# import subprocess # macOSとLinuxに対応させるためのライブラリ
from tkinter import *
from tkinter import messagebox
from PIL import Image, ImageTk, UnidentifiedImageError, ImageColor
from datetime import datetime, timedelta

# このスクリプトの絶対パス
scr_path = os.path.dirname(os.path.abspath(sys.argv[0]))

if sys.platform.startswith("win"):
    os.environ["VLC_PLUGIN_PATH"] = r"c:\Program Files\VideoLAN/VLC"

# VLC のインスタンスを作成
vlc_instance = vlc.Instance("--verbose=2") 

# NMSプロトコルを解消させるには, user-agent を新しいモノに偽装する必要性がある
# NSPlayer/12.0.7601.17514: Windows Media Player 12 の user-agent
# vlc_instance = vlc.Instance("--mms-user-agent=NSPlayer/12.0.7601.17514 --verbose=2")
# if vlc_instance is None:
#     print("エラー: VLCの初期化に失敗しました")
#     print("VLC media playerがインストールされているか確認してください")
#     print("Pythonのアーキテクチャ(32bit/64bit)と VLCのアーキテクチャを一致させる必要があります")
#     sys.exit(1) # プログラム終了
    
list_player = vlc_instance.media_list_player_new() # プレイリストを管理するプレイヤー
player = vlc_instance.media_player_new() # 実際に再生するプレイヤー
list_player.set_media_player(player) # 2つのプレイヤーを紐づけ

# サイマルラジオリスト(sample)
radio_station = {
    "FM わっぴ～(稚内市)": "mms://hdv5.nkansai.tv/wappy",
    "FM Kawaguchi(川口市)": "http://hdv4.nkansai.tv/kawaguchi",
    "京都三条ラジオカフェ": "mms://hdv3.nkansai.tv/radiocafe",
    "FM MOOV(神戸市)": "http://hdv4.nkansai.tv/fmmoov",
    "FM くめじま": "mms://hdv3.nkansai.tv/kumejima"
    }

# OpenWeatherMap の情報 (ex: 大阪市西成区萩之茶屋)
KEY = " 取得したAPI Key " # APIKey

LOCATION_SETTINGS = {
    "zip": "郵便番号,JP", # 郵便番号 カンマの後に必ず JP
    "display_name": " 郵便番号が対応している地域 " # 表示地域
}
# URL = "http://api.openweathermap.org/data/2.5/forecast?zip={0}&units=metric&lang=ja&APPID={1}"
URL = "http://api.openweathermap.org/data/2.5/forecast?zip={zip}&units=metric&lang=ja&APPID={key}"

# アラーム音
ALARM_SOUND_FILE = "countdown.mp3"
alarm_sound_path = os.path.join(scr_path, "sound", ALARM_SOUND_FILE)

# スヌーズ時刻
SNOOZE_MINUTES = 10 # 10分

original_wallpaper_pil = None  # オリジナルの壁紙を None に設定
bg_photo_image = None  # 背景画像を None に設定

try:
    # 背景画像を読み込む
    # WindowsXP.jpg は Microsoft 公式からダウンロードしたもの
    wallpaper_path = os.path.join(scr_path, "img", "WindowsXP.jpg") # 背景画像のパス
    original_wallpaper_pil = Image.open(wallpaper_path) # 背景画像を開く
except (FileNotFoundError, UnidentifiedImageError) as e:
    print(f"壁紙の読み込みエラー: {e}")
    
def recolor_image(image, new_color=(255, 255, 255)): # 画像を新しい色に変更
    img = image.convert("RGBA") # 画像をRGBAモードに変換
    data = img.getdata() # 画像のデータを取得

    new_data = [] # 新しい画像のデータ
    for item in data: # 各項目を処理
        if item[3] > 0: # アルファ値が0より大きい場合
            new_data.append(new_color + (item[3],)) # 新しい色とアルファ値を追加
        else:
            new_data.append(item) # 元の色とアルファ値を追加
    
    img.putdata(new_data) # 新しい画像のデータを設定
    return img # 新しい画像

# ===== ↓↓↓ スリープ制御 ↓↓↓ =====
"""
macOS や Linuxにも対応させてはいるが
動作については未検証なため
コメントアウトしているコードについては参考程度に
"""

# _caffeinaite_process = None
if sys.platform.startswith("win"):
    try:
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002

        def prevent_sleep():
            # スリープを防止
            print("ディスプレイのスリープを防止します。(Windows)")
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        
        def allow_sleep():
            # スリープを許可
            print("ディスプレイのスリープを許可します。(Windows)")
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        
    except (ImportError, AttributeError) as e:
        print(f"スリープの制御機能の初期化に失敗: {e}")
        # 初期化に失敗した場合のダミー関数を定義
        def prevent_sleep():
            pass
        
        def allow_sleep():
            pass

# === macOS ===        
# elif sys.platform == "darwin":
#     def prevent_sleep():
#         global _caffeinaite_process is None:
#         if _caffeinaite_process is None:
#           print("ディスプレイのスリープを防止します(macOS)")
#             -d: ディスプレイのスリープを防止, -i: アイドルスリープを防止
#             _caffeinaite_process = subprocess.Popen(["caffeinate", "-di"])
#    
#     def allow_sleep():
#         global _caffeinaite_process
#         if _caffeinaite_process is not None:
#             print("ディスプレイのスリープを許可します(macOS)")
#             _caffeinaite_process.terminate()
#             _caffeinaite_process = None

# === Linux ===
# elif:
#     sys.platform_startswith("linux"):
#         def prevent_sleep():
#             print("ディスプレイのスリープを防止します(Linux)")
#             try:
#                 subprocess.run(["xset", "s", "off", "-dpms"], check=True)
#             except (FileNotFoundError, subprocess.CalledProcessError) as e:
#                 print(f"xset コマンドの実行に失敗: {e}, スリープの制御は無効です")
#        
#         def allow_sleep():
#             print("ディスプレイのスリープを許可します(Linux)")
#             try:
#                 subprocess.run(["xset", "s", "on", "-dpms"], check=True)
#             except (FileExistsError, Subprocess.CalledProcessError) as e:
#                 print(f"xset コマンドの実行に失敗: {e}")
#               
# else:
#     def prevent_sleep():
#         print(f"このOS ({sys.platform}) はサポートされていません")
#        
#     def allow_sleep():
#         pass
# ===== ↑↑↑ スリープ制御 ↑↑↑ =====


# メインウィンドウ作成
root = Tk()

# メインウィンドウサイズ
root.geometry("1024x768")

# メインウィンドウタイトル (任意でタイトルを設定)
root.title("Weather Clock")


# MainFrame クラス
class MainFrame(Frame):

    # コンストラクタ
    def __init__(self, master=None, **kwargs):
        # 親クラスのコンストラクタを呼び出す
        super().__init__(master, **kwargs)
        
        # ボリューム調整
        self.radio_volume = 70 # サイマルラジオ
        self.alarm_volume = 80 # アラーム
        
        # アラーム用変数の初期化
        self.alarm_time = None # アラーム時刻
        self.alarm_triggered_today = False # 今日のアラームが発生したか
        self.last_checked_day = datetime.now().day # 最後にチェックした日付
        self.alarm_status_id = None # アラーム状態表示用のID
        self.snooze_id = None # スヌーズ処理用のID
        self.alarm_timeout_id = None # アラームタイムアウト用のID
        
        # サイマルラジオ再生状態の保存用
        self.radio_was_playing = False # サイマルラジオ再生中か
        self.last_played_radio_url = None # 最後に再生したラジオのURL
        self.current_station_name = None # 常時局名
        self.radio_station_id = None # 常時局名表示用のID
                
        # create_widgets を呼び出す
        self.create_widgets()

    # ウィジェットを作成(canvas)
    def create_widgets(self):

        # Canvas を作成
        self.canvas = Canvas(self, bd="0", highlightthickness=0) # highlightthickness=0 は外枠を消す
        self.canvas.pack(side=TOP, expand=1, fill=BOTH) # メインウィンドウに配置
        
        # 時刻表示
        self.wt_id = self.canvas.create_text(
            0,
            0, 
            text="",
            font=("", 160), 
            fill="black",
            anchor="center"
        )
        self.wallpaper_item_id = None
        
        # 日付表示
        self.wd_id = self.canvas.create_text(
            0,
            0,
            text="", 
            font=("", 60, "bold"), 
            fill="black",
            anchor="e"
        )
        
        # 曜日表示
        self.w_day_id = self.canvas.create_text(
            0,
            0,
            text="",
            font=("", 50, "bold"),
            fill="black", # デフォルト(平日)は黒
            anchor="w"
        )
        
        # 地域表示
        self.wp_id = self.canvas.create_text(
            0,
            0,
            text="",
            font=("", 20, "bold"),
            fill="black",
            anchor="nw"
        )
        
        # アラーム状態
        self.alarm_status_id = self.canvas.create_text(
            0,
            0,
            text="",
            font=("", 20, "bold"),
            fill="maroon",
            anchor="se"
        )
        
        # ラジオ再生状態
        self.radio_station_id = self.canvas.create_text(
            0,
            0,
            text="",
            font=("", 20, "bold"),
            fill="orange",
            anchor="nw"
        )
    
        # 天候アイコン（ディクショナリ）
        icon_files = {
            "01d":"01d.png", "01n":"01n.png",
            "02d":"02d.png", "02n":"02n.png",
            "03d":"03.png", "03n":"03.png",
            "04d":"04.png", "04n":"04.png",
            "09d":"05.png", "09n":"05.png",
            "10d":"06.png", "10n":"06.png",
            "11d":"07.png", "11n":"07.png",
            "13d":"08.png", "13n":"08.png",
            "50d":"09.png", "50n":"09.png"
        }

        self.icon_dict = {}

        try:
            icon_color_name = "white" # アイコンカラー
            icon_color = ImageColor.getrgb(icon_color_name)
        except ValueError:
            print(f"無効なカラー名: '{icon_color_name}'、デフォルト色を使用します。")
            icon_color = (255, 255, 255) # デフォルト色
        for key, filename in icon_files.items():
            try:
                img_path = os.path.join(scr_path, "img", filename) # 天候アイコンのパス
                original_image = Image.open(img_path) # 天候アイコンの読み込み
                recolored_image = recolor_image(original_image, new_color=icon_color) # 天候アイコンのカラー変更
                resized_image = recolored_image.resize((64, 64), Image.LANCZOS) # 天候アイコンのサイズ変更
                self.icon_dict[key]=ImageTk.PhotoImage(resized_image) # 天候アイコンの保存
            except (FileNotFoundError, UnidentifiedImageError) as e:
                print(f"天候アイコンの読み込みエラー: {e}")
                self.icon_dict[key] = None # 天候アイコンの保存
    
        self.wwl_ids = []  # 3時間おきの時系列
        self.wwi_ids = []  # 天候アイコン
        self.wwt_ids = []  # 気温表示
        self.wwr_ids = []  # 降水量表示

        for i in range(8):
            # 3時間おきの時間
            self.wwl_ids.append(self.canvas.create_text(
                0,
                0,
                text="",
                font=("", 30, "bold"),
                fill="white",
                anchor="n"
                ))
            
            # 天候アイコン
            self.wwi_ids.append(self.canvas.create_image(
                0,
                0,
                image=None,
                anchor="center"
                ))
            
            # 気温表示
            self.wwt_ids.append(self.canvas.create_text(
                0,
                0,
                text="",
                font=("", 20), 
                fill="white",
                anchor="n"
                ))
            
            # 降水量表示
            self.wwr_ids.append(self.canvas.create_text(
                0,
                0,
                text="",
                font=("", 20),
                fill="white",
                anchor="n"
                ))
            
def _reposition_canvas_items(event=None):
    # ウィンドウのサイズを取得
    if not hasattr(app, "canvas"):
        return

    canvas_width = app.canvas.winfo_width()
    canvas_height = app.canvas.winfo_height()
    
    if canvas_width < 1 or canvas_height < 1:
        return
    
    # 時刻の表示位置
    app.canvas.coords(app.wt_id, canvas_width * 0.5, canvas_height * 0.35)
    # 日付の表示位置
    date_y_pos = canvas_height * 0.10
    date_center_x = canvas_width * 0.5
    # 日付部分
    app.canvas.coords(app.wd_id, date_center_x - 5, date_y_pos)
    # 曜日部分
    app.canvas.coords(app.w_day_id, date_center_x + 25 , date_y_pos)
    # 地域の表示位置
    app.canvas.coords(app.wp_id, canvas_width * 0.05, canvas_height * 0.6)
    # ラジオ再生状態の表示位置
    app.canvas.coords(app.radio_station_id, canvas_width * 0.05, canvas_height * 0.50)
    # アラーム時刻の表示位置
    app.canvas.coords(app.alarm_status_id, canvas_width * 0.90, canvas_height * 0.52)
    
    weather_section_start_y_ratio = 0.7
    col_width_ratio = 1.0 / 8
    
    for i in range(8):
        x_center_ratio = (i * col_width_ratio) + (col_width_ratio / 2)
        x_center_abs = canvas_width * x_center_ratio
        # 時間帯を基準に
        app.canvas.coords(app.wwl_ids[i], x_center_abs, canvas_height * weather_section_start_y_ratio)
        # 天候アイコンの座標
        app.canvas.coords(app.wwi_ids[i], x_center_abs, canvas_height * (weather_section_start_y_ratio + 0.12))
        # 気温の座標
        app.canvas.coords(app.wwt_ids[i], x_center_abs, canvas_height * (weather_section_start_y_ratio + 0.18))
        # 降水量の座標
        app.canvas.coords(app.wwr_ids[i], x_center_abs, canvas_height * (weather_section_start_y_ratio + 0.22))
    
# メインフレームを配置
app=MainFrame(root)
app.pack(side=TOP, expand=1, fill=BOTH)

# 背景画像ラベルをリサイズ
def _resize_and_apply_wallpaper():
    global bg_photo_image, original_wallpaper_pil
    if original_wallpaper_pil is None:
    # 背景画像が設定されていない場合は何もしない
        if hasattr(app, "canvas") and app.wallpaper_item_id:
            app.canvas.delete(app.wallpaper_item_id)
            app.wallpaper_item_id = None
            app.canvas.configure(bg=root.cget("bg"))
        return
    
    root.update_idletasks()  # ウィンドウのサイズを更新
    
    win_width=root.winfo_width()
    win_height=root.winfo_height()
    
    if win_width <= 1 or win_height <= 1:
        # ウィンドウのサイズが不正な場合は何もしない
        return
    
    try:
        image_resized = original_wallpaper_pil.resize((win_width, win_height), Image.LANCZOS) # リサイズ
        bg_photo_image = ImageTk.PhotoImage(image_resized) # ImageTk.PhotoImageに変換
        
        if hasattr(app, "canvas"): # ウィンドウが作成されている場合
            if app.wallpaper_item_id: # 前回の壁紙を削除
                app.canvas.delete(app.wallpaper_item_id)
            app.wallpaper_item_id = app.canvas.create_image(0, 0, anchor="nw", image=bg_photo_image) # 新しい壁紙を配置
            app.canvas.tag_lower(app.wallpaper_item_id) # 壁紙を一番下に配置
        else:
            pass
        
    except Exception as e:
        print(f"壁紙のサイズ変更 / 適用エラー: {e}")

# 背景画像ラベルの読込
def load_new_wallpaper(image_path):
    global original_wallpaper_pil
    try:
        if not os.path.exists(image_path): # 画像ファイルが存在しない場合
            print(f"指定された画像ファイルが存在しません: {image_path}")
            original_wallpaper_pil = None # 背景画像を削除
            _resize_and_apply_wallpaper() # 背景画像を更新
            return

        temp_image = Image.open(image_path) # 画像を開く

        if temp_image.mode != "P": # 画像のモードがP以外の場合
            temp_image = temp_image.convert("RGBA")  # RGBAモードに変換
        elif temp_image.mode == "RGB": # 画像のモードがRGBの場合
            temp_image = temp_image.convert("RGB") # RGBモードに変換
        original_wallpaper_pil = temp_image # 背景画像を保存
        _resize_and_apply_wallpaper()
        
    except FileNotFoundError:
        print(f"指定されたファイルが見つかりません: {image_path}")
        original_wallpaper_pil = None
        _resize_and_apply_wallpaper()
        
    except UnidentifiedImageError:
        print(f"指定されたファイルは画像ではありません: {image_path}")
        original_wallpaper_pil = None
        _resize_and_apply_wallpaper()
    
    except Exception as e:
        print(f"画像の読み込みエラー: {e}")
        original_wallpaper_pil = None
        _resize_and_apply_wallpaper()

# 背景画像ラベルの選択
def select_wallpaper_dialog():
    from tkinter import filedialog
    file_path = filedialog.askopenfilename(
    title="画像ファイルを選択してください",
    filetypes=(("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All files", "*.*"))
    )
    if file_path:
        load_new_wallpaper(file_path)
        

def open_alarm_dialog():
    # アラーム設定ダイアログを開く
    dialog = Toplevel(root) # 新しいウィンドウを作成
    dialog.title("アラーム設定") # タイトル
    dialog.geometry("300x120") # ウィンドウサイズ
    dialog.resizable(False, False) # サイズ変更不可
    dialog.transient(root) # 親ウィンドウの上に表示
    
    Label(dialog, text="時刻設定 ( 24時間表記 ):", font=('', 12)).pack(pady=5) # ラベル
    time_frame = Frame(dialog) # 時刻設定フレーム
    time_frame.pack(pady=5) # フレームに配置
    # 時刻変数
    hour_var = StringVar(value=app.alarm_time.split(":")[0] if app.alarm_time else "07")
    # 分変数
    minute_var = StringVar(value=app.alarm_time.split(":")[1] if app.alarm_time else "00")
    
    # 時刻入力フィールド
    hour_entry = Entry(time_frame, textvariable=hour_var, width=5, font=("", 12), justify="center")
    hour_entry.pack(side=LEFT, padx=5) # フレームに配置
    # ラベル
    Label(time_frame, text=":", font=('', 12)).pack(side=LEFT)
    # 分入力フィールド
    minute_entry = Entry(time_frame, textvariable=minute_var, width=5, font=("", 12), justify="center") 
    minute_entry.pack(side=LEFT, padx=5)
    
    def set_alarm():
        # アラーム時刻を設定
        try:
            h = int(hour_var.get()) # 時
            m = int(minute_var.get()) # 分
            if not (0 <= h <= 23 and 0 <= m <= 59): # 時刻の範囲
                raise ValueError # 値エラー
        
            app.alarm_time = f"{h:02d}:{m:02d}" # アラーム時刻
            app.alarm_triggered_today = False # アラーム発生日
            app.canvas.itemconfigure(app.alarm_status_id, text=f"⏰ {app.alarm_time}") # アラームステータス
            print (f"アラームを設定しました: {app.alarm_time}")
            dialog.destroy() # ダイアログを閉じる
        except ValueError:
            messagebox.showerror("入力エラー","時(0-23)と分(0-59)を正確に…")
        
    def clear_alarm():
        # アラーム時刻をクリア
        app.alarm_time = None
        app.canvas.itemconfigure(app.alarm_status_id, text="") # アラームステータスをクリア
        
        # アラーム動作中, 通常の停止処理を呼び出す
        # alarm_timeout_id はアラーム動作中にのみ設定される
        if app.alarm_timeout_id:
            stop_alarm() # スケジュールされたアラームやスヌーズをキャンセル
        # スヌーズがスケジュールされているだけの場合, スケジュールをキャンセルする
        elif app.snooze_id:
            root.after_cancel(app.snooze_id) # スヌーズをキャンセル
            app.snooze_id = None # スヌーズIDをリセット
            print ("スヌーズをキャンセルしました")
        
        print("アラームを解除しました")
        dialog.destroy() # ダイアログを閉じる
    
    button_frame = Frame(dialog) # ボタンフレーム
    button_frame.pack(pady=10) # フレームに配置
    Button(button_frame, text=" 設定 ", font=("", 12), command=set_alarm, fg="blue").pack(side=LEFT, padx=10)
    Button(button_frame, text=" 解除 ", font=("", 12), command=clear_alarm).pack(side=LEFT, padx=10)
    Button(button_frame, text="キャンセル", font=("", 12), command=dialog.destroy, fg="red").pack(side=LEFT, padx=10)  

def trigger_alarm():
    # スヌーズ中だった場合は、表示を元に戻す
    app.canvas.itemconfigure(app.alarm_status_id, text=f"⏰ {app.alarm_time}")
    
    print(f"アラーム時刻({app.alarm_time})です")
    if not os.path.exists(alarm_sound_path):
        print("アラーム音ファイルが見つかりません")
        return

    # 既存の再生を停止
    if list_player.is_playing(): # 再生中の場合
        if app.last_played_radio_url: # ラジオを再生していた場合
            app.radio_was_playing = True # ラジオ再生状態を記録
            print("一時停止")
            # ラジオ再生状態の表示を削除
            app.canvas.itemconfigure(app.radio_station_id, text="")
        list_player.stop() # 再生を停止
    
    # アラーム用のメディアとプレイリストを作成
    media = vlc_instance.media_new(alarm_sound_path) # アラーム音
    media_list = vlc_instance.media_list_new([media]) # プレイリスト
    
    # プレイリストをセット
    list_player.set_media_list(media_list)
    
    # ループ再生モードに設定
    list_player.set_playback_mode(vlc.PlaybackMode.loop) # ループ再生モードに設定
    player.audio_set_volume(app.alarm_volume) # ボリューム(アラーム)設定
    list_player.play()
    
    # 60秒後にアラームを自動停止するタイマー
    if app.alarm_timeout_id: # 既にタイマーが設定されている場合
        root.after_cancel(app.alarm_timeout_id) # タイマーをキャンセル
    app.alarm_timeout_id = root.after(60000, stop_alarm) # 60秒後にアラームを自動停止
    
    current_width = root.winfo_width() # 現在のウィンドウ幅を取得
    alarm_stop_btn.place(x=root.winfo_width() - 125, y = 95) # アラーム解除ボタンの配置
    snooze_btn.place(x=root.winfo_width() - 125, y = 135) # スヌーズ(10分)ボタンの配置
    app.alarm_triggered_today = True # 今日のアラームが発生
    
def stop_alarm():
    # スケジュールされた自動停止をキャンセル
    if app.alarm_timeout_id: # 既にタイマーが設定されている場合
        root.after_cancel(app.alarm_timeout_id) # タイマーをキャンセル
        app.alarm_timeout_id = None # タイマーIDをリセット
        
    if list_player.is_playing():
        list_player.stop()
        # デフォルトモードに戻す
        list_player.set_playback_mode(vlc.PlaybackMode.default)
        print("アラーム停止")
        
    # 一時停止していたラジオを再開
    if app.radio_was_playing and app.last_played_radio_url: # ラジオを一時停止していた場合
        def resume_radio():
            # ラジオを再開
            print("サイマルラジオ再生再開")
            play_radio(app.last_played_radio_url, resume=True) # ラジオを再開
            # アラームシーケンスが完了したので, フラグをリセット
            app.radio_was_playing = False # ラジオ再生状態をリセット
        # player の状態が安定するのを待ってから再生を再開    
        root.after(100, resume_radio)
        
    if app.snooze_id: # スヌーズ中の場合
        root.after_cancel(app.snooze_id) # スヌーズをキャンセル
        app.snooze_id = None # スヌーズIDをリセット
        print ("スヌーズをキャンセル")
    
    alarm_stop_btn.place_forget() # アラーム解除ボタンを非表示
    snooze_btn.place_forget() # スヌーズ(10分)ボタンを非表示
    
def snooze_alarm():
    # スケジュールされた自動停止をキャンセル
    if app.alarm_timeout_id: # 既にタイマーが設定されている場合
        root.after_cancel(app.alarm_timeout_id) # タイマーをキャンセル
        app.alarm_timeout_id = None # タイマーIDをリセット
    
    if list_player.is_playing():
        list_player.stop()
        # デフォルトモードに戻す
        list_player.set_playback_mode(vlc.PlaybackMode.default)
        
    # 一時停止しているサイマルラジオを再開
    if app.radio_was_playing and app.last_played_radio_url: # ラジオを一時停止していた場合
        def resume_radio_snooze():
            print("サイマルラジオ再生再開(スヌーズ中)")
            play_radio(app.last_played_radio_url, resume=True) # ラジオを再開
        # player の状態が安定するの待ってから再生を再開
        root.after(100, resume_radio_snooze) # 100ミリ秒後に再生を再開
            
    alarm_stop_btn.place_forget() # アラーム解除ボタンを非表示
    snooze_btn.place_forget() # スヌーズ(10分)ボタンを非表示
    app.canvas.itemconfigure(app.alarm_status_id, text=f"⏰ {app.alarm_time} (スヌーズ中…)") # アラームステータスを更新
    print(f"{SNOOZE_MINUTES}分後に再度アラームを設定します")
    app.snooze_id = root.after(SNOOZE_MINUTES * 60 * 1000, trigger_alarm) # 10分後にスヌーズを設定
        
# メインウィンドウを閉じる
def wm_close():
    if list_player.is_playing():
        list_player.stop()
    if app.snooze_id:
        root.after_cancel(app.snooze_id) # スヌーズをキャンセル
    vlc_instance.release()  # VLC インスタンスを解放
    allow_sleep()  # スリープ抑制を解除
    # メインウィンドウを破棄
    root.destroy()

# === ↓↓↓ ボタン生成 ↓↓↓ ===
# 壁紙変更    
wallpaper_btn=Button(
    root, 
    text=" 壁紙変更 ", 
    font=("", 12), 
    relief=FLAT,
    command=select_wallpaper_dialog
    )

# プログラム終了
close_btn=Button(
    root, 
    text="プログラム終了",
    font=("", 12), 
    fg="red",
    relief=FLAT,
    command=wm_close
    )

# アラーム設定
alarm_set_btn = Button(
    root,
    text="アラーム設定",
    font=("", 12),
    fg="blue",
    relief=FLAT,
    command=open_alarm_dialog
)

# アラーム解除
alarm_stop_btn = Button(
    root,
    text="アラーム解除",
    font=("", 12),
    relief=FLAT,
    command=stop_alarm,
    bg="tomato"
)
alarm_stop_btn.place_forget() # 初期状態では非表示

# スヌーズ
snooze_btn = Button(
    root,
    text=f"スヌーズ({SNOOZE_MINUTES}分)",
    font=("", 12),
    relief=FLAT,
    command=snooze_alarm,
    bg="pink2"
)
# === ↑↑↑ ボタン生成 ↑↑↑ ===

# 画面リサイズ
def change_size(event):
    """
    リサイズしてもボタンの位置がズレない仕様
    """
    # ボタンの位置を右上に
    current_width = root.winfo_width()
    if current_width > 1:
        
        wallpaper_btn.place(x=current_width - 125, y=15) # 壁紙変更ボタンの配置
        alarm_set_btn.place(x=current_width - 125, y=55) # アラーム設定ボタンの配置
        close_btn.place(x=current_width - 125, y=175) # プログラム終了ボタンの配置
        # === ↓↓↓ アラーム再生時に表示される ↓↓↓ ===
        if alarm_stop_btn.winfo_ismapped():
            alarm_stop_btn.place(x=current_width - 125, y = 95) # アラーム解除ボタンの配置
        if snooze_btn.winfo_ismapped():
            snooze_btn.place(x=current_width - 125, y = 135) # スヌーズボタン(初回)の配置
        # === ↑↑↑ アラーム再生時に表示される ↑↑↑ ===
    if original_wallpaper_pil is not None:
        # 背景画像をリサイズして適用
        _resize_and_apply_wallpaper()
        
    _reposition_canvas_items() # 位置を再計算
        
# 画面のリサイズをバインドする
root.bind('<Configure>', change_size)

def update_time():
    # 現在日時を表示
    now = datetime.now() # 現在日時
    
    if app.last_checked_day != now.day: # 日付が変わった場合
        app.alarm_triggered_today = False # アラームフラグをリセット
        app.last_checked_day = now.day # 日付を更新
        print("日付が変わりました, アラームフラグをリセットします")
    
    if (app.alarm_time is not None and # アラーム時刻が設定されている場合
        not app.alarm_triggered_today and # アラームが発生していない場合
        now.strftime("%H:%M") == app.alarm_time): # 現在時刻とアラーム時刻が一致する場合
        trigger_alarm() # アラームを発生
    
    # 日付と時刻の文字列を作成
    date_str = f"{now.year:0>4d}/{now.month:0>2d}/{now.day:0>2d}" # 日付
    day_of_week_str = f"( {now.strftime('%a')}. )" # 曜日
    time_str = f"{now.hour:0>2d}:{now.minute:0>2d}:{now.second:0>2d}" # 時刻
    
    # 曜日の文字色を指定
    weekday = now.weekday() # 月曜が0, 日曜が6
    is_holiday = jpholiday.is_holiday(now.date()) # 祝日判定
    
    day_color = "black" # デフォルト
    if is_holiday: # 祝日は赤
        day_color = "red" 
    elif weekday == 6: # 日曜
        day_color = "red"
    elif weekday == 5: # 土曜
        day_color = "blue"
        
    # canvas のテキストを更新
    app.canvas.itemconfigure(app.wd_id, text=date_str) # 日付
    app.canvas.itemconfigure(app.w_day_id, text=day_of_week_str, fill=day_color) # 曜日
    app.canvas.itemconfigure(app.wt_id, text=time_str) # 時刻

    # 1秒間隔で繰り返す
    root.after(1000, update_time)
      
def update_weather():
    # 表示カウンタ
    count=0 # 現在の表示カウンタ

    # URL を作成して OpenWeatherMap に問い合わせを行う
    url = URL.format(zip=LOCATION_SETTINGS["zip"], key=KEY)
    try:
        # 10秒のタイムアウトを設定, エラーがあれば例外を発生させる
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # エラーを確認
        forecastData = json.loads(response.text)
    except requests.exceptions.RequestException as e:
        print(f"情報取得に失敗しました: {e}")
        app.canvas.itemconfigure(app.wwi_id, text="情報取得できません" )
        root.after(60000, update_weather) # 60秒後に再度実行
        return

    # 結果が得られない場合は即時終了
    if not ("list" in forecastData):
        print("エラー: データが不正な形式です")
        return

    # デバッグ用
    print(forecastData)

    # 結果を 3 時間単位で取得
    for item in forecastData["list"]:
        # 時間帯を 24 時間表記で表示
        forecastDatetime = datetime.fromtimestamp(item["dt"])
        app.canvas.itemconfigure(app.wwl_ids[count], text=forecastDatetime.hour)

        # 気候をアイコンで表示
        app.canvas.itemconfigure(app.wwi_ids[count], image=app.icon_dict[item["weather"][0]["icon"]])

        # 気温を表示
        app.canvas.itemconfigure(app.wwt_ids[count], text="{0}°c".format(round(item["main"]["temp"])))

        # 降水量を表示
        rainfall = 0
        if "rain" in item and "3h" in item["rain"]:
            rainfall = item["rain"]["3h"]
        app.canvas.itemconfigure(app.wwr_ids[count], text="{0}mm".format(math.ceil(rainfall)))

        # 表示カウンタを更新
        count += 1 # カウンタを 1 増やす

        # 全て表示し終えたらループ終了
        if count >= len(app.wwl_ids):
            # 地域情報を表示
            app.canvas.itemconfigure(app.wp_id, text="{0} (Latitude:{1}, Longitude:{2})".format( # 地域
                LOCATION_SETTINGS["display_name"], # 漢字表記の地域名
                forecastData["city"]["coord"]["lat"], # 緯度 Latitude
                forecastData["city"]["coord"]["lon"])) # 経度 Longitude

            # 60 秒間隔で繰り返す
            root.after(60000, update_weather)
            
            return

# ===== ↓↓↓ サイマルラジオ再生 ↓↓↓ =====
def get_stream_url_from_asx(asx_location):
    # ASXファイルを取得
    try:
        content = ""  # ASXファイルの内容
        # URL または Local ASXファイルか判定
        if asx_location.lower().startswith(("http://", "https://", "mms://", "mmsh://")):
            print(f"ASXファイルをURLから取得します: {asx_location}")
            response = requests.get(asx_location, timeout=10)  # 10秒のタイムアウト
            response.raise_for_status()  # エラーを確認
            content = response.text  # ASXファイルの内容
        else:
            print(f"ASXファイルをローカルから取得します: {asx_location}")
            # さまざまなエンコーディングでASXファイルを読み込む(エラーを無視)
            # with open(asx_location, "r", encoding="utf-8", errors="ignore") as f:
                # content = f.read()
            
            encodings_to_try = ["utf-8", "shift_jis", "cp932", "euc_jp"] # 読み込み可能なエンコーディング
            for encoding in encodings_to_try:
                # さまざまなエンコーディングでASXファイルを読み込む
                try:
                    with open(asx_location, "r", encoding=encoding) as f: # 読み込み可能なエンコーディングでASXファイルを読み込む
                        content = f.read() # ASXファイルの内容
                        print(f"エンコーディング '{encoding}' での読込成功")
                    break
                except (UnicodeDecodeError, TypeError):
                    # print(f"エンコーディング '{encoding}' での読込失敗")
                    continue
            if not content:
                print("どのエンコーディングでもファイル読込に失敗")
                
        print("--- ASXファイルの内容 ---")
        print(content)
        print("----------------------")
    
        # ASXファイルからStream URLを抽出(柔軟な正規表現を使用)
        match = re.search(r'<ref\s+href\s*=\s*["\'](.*?)["\']', content, re.IGNORECASE) # 大文字小文字を区別しない
        if match: # Stream URLが見つかった場合
            stream_url = match.group(1) # Stream URL
            print(f"Stream URLが見つかりました: {stream_url}")
            return stream_url
        else:
            print("ASX fileからStream URLが見つかりません.")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"ASX fileの取得中にエラー: {e}")
        return None
    
    except Exception as e:
        print(f"予期せぬエラー: {e}")
        return None

# サイマルラジオの再生を行う関数
def play_radio(location, resume=False): # resume は再生状態を更新するかどうかのフラグ
    if list_player.is_playing(): # 再生中の場合
        list_player.stop() # 再生を停止
        
    station_name = None # ラジオ局名
    # URL からラジオ局名を探す
    for name, url in radio_station.items(): # radio_station は辞書
        if url == location: # URL と一致する場合
            station_name = name # ラジオ局名
            break
    
    # ローカルファイルの場合, ファイル名を取得
    if not station_name and os.path.exists(location): # ローカルファイルの場合
        station_name = os.path.basename(location) # ファイル名
    # それでも見つからない場合は
    if not station_name: # ラジオ局名が見つからない場合
        station_name = "ストリーミング" # デフォルトのラジオ局名
    
    # resume がFalse の時(通常再生)のみ, 再生状態を更新
    if not resume: # 通常再生の場合
        app.last_played_radio_url = location # 再生したURLを保存
        app.radio_was_playing = False # 一時停止ではないのでリセット
        
    # 常時局名を更新し, 表示する
    app.current_station_name = station_name # ラジオ局名
    # 再生中のラジオ局名を表示
    app.canvas.itemconfigure(app.radio_station_id, text=f"🎵 再生中: {app.current_station_name}") 
    
    stream_url = location
    # mms, rtmp, rtsp 以外のプロトコルはASXとみなし, Stream URL を抽出
    if not location.lower().startswith(("mms://", "rtmp://", "rtsp://")): # プロトコルがmms, rtmp, rtsp 以外の場合
        extracted_url = get_stream_url_from_asx(location) # Stream URL を抽出
        if extracted_url: # Stream URL を抽出できた場合
            stream_url = extracted_url # Stream URL を更新
            
    # if location.lower().endswith(".asx"):
    #     stream_url = get_stream_url_from_asx(location)
    if not stream_url:
        print("再生可能なストリームURLが見つかりません")
        return
    
    if stream_url.lower().startswith("http://hdv"): # http://hdv から始まる場合
        print(f"ストリームURLをhttpからmmsに変換します: {stream_url}")
        stream_url = stream_url.replace("http://", "mms://", 1) # http:// を mms:// に変換
        print(f"変換後のストリームURL: {stream_url}")
    
    # ラジオ用のメディアとプレイリストを作成
    media = vlc_instance.media_new(stream_url) 
    media_list = vlc_instance.media_list_new([media])
    
    # プレイリストをセット
    list_player.set_media_list(media_list)
    
    # 通常モードに設定(ループしない)
    list_player.set_playback_mode(vlc.PlaybackMode.default)
    player.audio_set_volume(app.radio_volume) # ボリューム(サイマルラジオ)設定
    list_player.play()
    print(f"再生を試行します: {stream_url}")
    
# サイマルラジオの再生を停止する関数
def stop_radio():
    if list_player.is_playing(): # 再生中の場合
        list_player.stop() # 再生を停止
        print("ラジオ停止")
    
    # 再生状態の表示を消す
    app.canvas.itemconfigure(app.radio_station_id, text="")
    # 手動停止のため, 自動再生しないよう情報をクリア
    app.last_played_radio_url = None # 再生したURLをクリア
    app.radio_was_playing = False # ラジオ再生状態をリセット
    app.current_station_name = None # ラジオ局名をクリア
    
    
def select_and_play_local_asx():
    # ASXファイルを選択して再生
    from tkinter import filedialog 
    file_path = filedialog.askopenfilename( # ASXファイルを選択
        title="ASXファイルを選択してください",
        filetypes=(("ASX files", "*.asx"), ("All files", "*.*"))
    )
    if file_path:
        play_radio(file_path)
        
def open_volume_dialog():
    # 音量設定ダイアログを開く
    dialog = Toplevel(root) # 新しいウィンドウを作成
    dialog.title("音量設定") # タイトル
    dialog.geometry("300x215") # ウィンドウサイズ
    dialog.resizable(False, False) # サイズ変更不可
    dialog.transient(root) # 親ウィンドウの上に表示
    
    # ラジオ音量
    Label(dialog, text="サイマルラジオ音量:", font=('', 12)).pack(pady=(10, 0)) # ラベル
    radio_volume_scale = Scale(dialog, from_=0, to=100, orient=HORIZONTAL) # スライダー
    radio_volume_scale.set(app.radio_volume) # 初期値
    radio_volume_scale.pack(pady=5, padx=20, fill=X) # フレーム
    
    # アラーム・スヌーズ音量
    Label(dialog, text="アラーム音量:", font=('', 12)).pack(pady=(10, 0))
    alarm_volume_scale = Scale(dialog, from_=0, to=100, orient=HORIZONTAL) # スライダー
    alarm_volume_scale.set(app.alarm_volume) # 初期値
    alarm_volume_scale.pack(pady=5, padx=20, fill=X) # フレーム
    
    # dialog を開いたときにスライダーにフォーカスを充てる
    radio_volume_scale.focus_set()
    
    # スライダーの値を増減させる
    def adjust_volume(scale_widget, delta):
        current_value = scale_widget.get() # 現在の値
        new_value = current_value + delta # 変更後の値
        # 値が 0 - 100 の範囲に収まるようにする
        if 0 <= new_value <= 100:
            scale_widget.set(new_value)
            
    # キーボード操作用のハンドラ, デフォルトの動作を上書きするため break を返す
    def key_adjust_volume(event, scale_widget, delta): 
        adjust_volume(scale_widget, delta) # スライダーの値を増減させる
        return "break"
    
    # === ↓↓↓ キーバインド ↓↓↓ ===
    # 音量スライダー(ラジオ)
    radio_volume_scale.bind("<Left>", lambda e: key_adjust_volume(e, radio_volume_scale, -1))
    radio_volume_scale.bind("<Right>", lambda e: key_adjust_volume(e, radio_volume_scale, 1))
    radio_volume_scale.bind("<Up>", lambda e: key_adjust_volume(e, radio_volume_scale, 1))
    radio_volume_scale.bind("<Down>", lambda e: key_adjust_volume(e, radio_volume_scale, -1))
    # 音量スライダー(アラーム)
    alarm_volume_scale.bind("<Left>", lambda e: key_adjust_volume(e, alarm_volume_scale, -1))
    alarm_volume_scale.bind("<Right>", lambda e: key_adjust_volume(e, alarm_volume_scale, 1))
    alarm_volume_scale.bind("<Up>", lambda e: key_adjust_volume(e, alarm_volume_scale, 1))
    alarm_volume_scale.bind("<Down>", lambda e: key_adjust_volume(e, alarm_volume_scale, -1))
    # === ↑↑↑ キーバインド ↑↑↑ ===

    def apply_volume():
        # 音量を設定
        app.radio_volume = radio_volume_scale.get() 
        app.alarm_volume = alarm_volume_scale.get()
        # 再生中のラジオがあれば即時反映
        if list_player.is_playing() and app.last_played_radio_url:
            player.audio_set_volume(app.radio_volume)
        print(f"音量を設定しました: ラジオ={app.radio_volume}, アラーム={app.alarm_volume}")
        dialog.destroy()
        
    button_frame = Frame(dialog)
    button_frame.pack(pady=10)
    Button(button_frame, text=" OK ", font=("", 12), command=apply_volume, fg="blue").pack(side=LEFT, padx=10)
    Button(button_frame, text="キャンセル", font=("", 12), command=dialog.destroy, fg="red").pack(side=LEFT, padx=10)
        
# メニューの設定
def setup_menus(): 
    # メニューバー
    menu_bar = Menu(root)
    # ラジオメニュー
    radio_menu = Menu(menu_bar, tearoff=0)
    
    for name, url in radio_station.items(): # radio_station は辞書
        radio_menu.add_command(label=name, command=lambda loc=url: play_radio(loc)) # ラジオを再生
    
    radio_menu.add_separator() # セパレータ
    radio_menu.add_command(label="ローカルASXファイルから再生", command=select_and_play_local_asx)
    radio_menu.add_separator()
    radio_menu.add_command(label="停止", command=stop_radio)
    
    menu_bar.add_cascade(label="Radio", menu=radio_menu) # メニューバーに追加
    
    # 設定メニュー
    settings_manu = Menu(menu_bar, tearoff=0) # メニューを作成
    settings_manu.add_command(label="音量設定", command=open_volume_dialog) # 音量設定
    menu_bar.add_cascade(label="設定", menu=settings_manu) # メニューバーに追加
    
    root.config(menu=menu_bar) # メニューバーを設定
    
setup_menus() 

# =====  ↑↑↑ サイマルラジオ再生  ↑↑↑ =====
# 初回起動
app.last_checked_day = datetime.now().day # 最後にチェックした日付
update_time() # 時刻の初回と定期更新
update_weather() # 天気の初回と定期更新

#稼働中のスリープ防止
prevent_sleep()

# メインループ
root.mainloop()
