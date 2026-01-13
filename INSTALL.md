# 安裝與執行指南 (Installation Guide)

本文件將引導您如何在 Windows 環境下設定並執行 QuickPaste。

## 📋 前置需求

*   **作業系統**: Windows 10/11 (建議 64-bit)
*   **Python 版本**: Python 3.8 或更高版本

## 步驟 1: 安裝 Python

如果您尚未安裝 Python，請前往 [Python 官方網站](https://www.python.org/downloads/) 下載並安裝。
*   **重要**：安裝時請務必勾選 **"Add Python to PATH"** 選項。

## 步驟 2: 下載專案

將本專案資料夾下載至您的電腦任意位置。

## 步驟 3: 安裝依賴套件

建議使用命令提示字元 (CMD) 或 PowerShell 進入專案目錄安裝所需的套件。

1.  開啟終端機 (Win+R 輸入 `cmd`)。
2.  切換到專案目錄：
    ```cmd
    cd C:\您的路徑\Auto_Paste_Script
    ```
3.  執行以下指令安裝依賴：
    ```cmd
    pip install -r requirements.txt
    ```

    *這將會安裝 `PyQt6`, `keyboard`, `pyperclip` 等必要套件。*

## 步驟 4: 執行程式

安裝完成後，您可以使用以下指令啟動程式：

```cmd
python app.py
```

### 💡 常見問題排除

**Q: 執行後視窗出現但快捷鍵沒反應？**
*   **A**: 請嘗試以「系統管理員身分」執行命令提示字元 (Right-click CMD -> Run as Administrator)，然後再執行 `python app.py`。Windows 的安全機制有時會攔截普通權限程式的全域鍵盤監聽。

**Q: 出現 `ModuleNotFoundError`？**
*   **A**: 請確認您是否已正確執行步驟 3 的 `pip install` 指令，且沒有報錯。

**Q: 防毒軟體報警？**
*   **A**: 本程式使用了 `keyboard` 模組來實現全域快捷鍵，這類行為有時會被誤判為 Keylogger。請將程式目錄加入防毒軟體的排除清單。
