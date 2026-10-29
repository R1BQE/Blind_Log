import requests
import threading
import webbrowser
import wx

from i18n import tr
from utils import get_version, Result
from update_service import version_tuple, perform_update_check as _perform_update_check
from update_installer import _download_and_update_worker


def check_update(parent_frame, silent_if_latest=False):
    """Проверяет наличие обновлений и запускает процесс обновления в фоне."""
    thread = threading.Thread(target=_check_update_worker, args=(parent_frame, silent_if_latest), daemon=True)
    thread.start()
    return thread


def perform_update_check():
    """Compatibility wrapper; keep dependencies patchable for existing callers/tests."""
    return _perform_update_check(get_version_fn=get_version, request_get=requests.get)


def _check_update_worker(parent_frame, silent_if_latest):
    result = perform_update_check()

    if not result.success:
        wx.CallAfter(wx.MessageBox, result.error, tr("error.title"), wx.OK | wx.ICON_ERROR)
        return

    update_info = result.data
    if not update_info.get("update_available", False):
        if not silent_if_latest:
            wx.CallAfter(
                wx.MessageBox,
                tr("update.up_to_date").format(version=update_info.get("current_version", "")),
                tr("update.title"),
                wx.OK | wx.ICON_INFORMATION
            )
        return

    wx.CallAfter(
        _show_update_dialog,
        parent_frame,
        update_info["latest_version"],
        update_info["current_version"],
        update_info["changelog"],
        update_info["download_url"]
    )


def _show_update_dialog(parent_frame, latest_version, current_version, changelog, download_url):
    dlg = wx.Dialog(parent_frame, title=tr("update.title"), size=(600, 500))
    vbox = wx.BoxSizer(wx.VERTICAL)
    info = wx.StaticText(dlg, label=tr("update.changelog_info"))
    vbox.Add(info, 0, wx.ALL, 10)
    text_ctrl = wx.TextCtrl(dlg, value=changelog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    vbox.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 10)
    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_update = wx.Button(dlg, label=tr("button.update"))
    btn_manual = wx.Button(dlg, label=tr("button.manual_download"))
    btn_cancel = wx.Button(dlg, label=tr("button.cancel"))
    btn_sizer.Add(btn_update, 0, wx.RIGHT, 10)
    btn_sizer.Add(btn_manual, 0, wx.RIGHT, 10)
    btn_sizer.Add(btn_cancel, 0)
    vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
    dlg.SetSizer(vbox)

    result = [None]

    def on_update(evt):
        result[0] = "update"
        dlg.Close()

    def on_manual_download(evt):
        # Не закрываем диалог - пользователь может посмотреть changelog
        # и потом всё-таки нажать "Обновить", если передумает.
        # Ссылка всегда указывает на последний релиз и не зависит от
        # того, ответил ли GitHub API на этот конкретный запрос -
        # поэтому она работает как надёжный запасной вариант, даже
        # если automatic update недоступен по какой-то причине.
        webbrowser.open("https://github.com/r1bqe/Blind_Log/releases/latest/download/Blind_log.zip")

    def on_cancel(evt):
        result[0] = "cancel"
        dlg.Close()

    btn_update.Bind(wx.EVT_BUTTON, on_update)
    btn_manual.Bind(wx.EVT_BUTTON, on_manual_download)
    btn_cancel.Bind(wx.EVT_BUTTON, on_cancel)
    dlg.ShowModal()
    dlg.Destroy()

    if result[0] != "update":
        return

    _start_download_thread(download_url, parent_frame)


def _start_download_thread(download_url, parent_frame):
    progress_dialog = wx.ProgressDialog(
        tr("update.downloading"),
        tr("update.preparing"),
        maximum=100,
        parent=parent_frame,
        style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL | wx.PD_CAN_ABORT
    )
    cancel_event = threading.Event()

    def _update_progress_ui(percent, message):
        keep_going = progress_dialog.Update(percent, message)
        if not keep_going:
            cancel_event.set()

    def update_progress(percent, message):
        wx.CallAfter(_update_progress_ui, percent, message)

    def worker():
        result = _download_and_update_worker(download_url, parent_frame, update_progress, cancel_event)
        wx.CallAfter(_on_download_finished, result, progress_dialog, parent_frame)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def _on_download_finished(result, progress_dialog, parent_frame):
    try:
        if progress_dialog:
            progress_dialog.Destroy()
    except (OSError, RuntimeError):
        pass

    if not result.success:
        wx.MessageBox(tr("update.error").format(error=result.error), tr("error.title"), wx.OK | wx.ICON_ERROR)
    else:
        # Close main window only if it exists and is visible
        try:
            if parent_frame is not None and parent_frame.IsShown():
                parent_frame.Close()
        except Exception:
            pass


