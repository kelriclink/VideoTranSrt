#pragma once

#include <QDialog>
#include <QTableWidget>
#include <QPushButton>
#include <QLabel>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QProgressBar>
class QThread;

class QLineEdit;

namespace v2s { struct ModelInfo; }

class ModelManagerDialog : public QDialog {
    Q_OBJECT
public:
    explicit ModelManagerDialog(QWidget* parent = nullptr);
    ~ModelManagerDialog() override = default;

private:
    void setupUi();
    void refresh();
    int selectedRow() const;

private slots:
    void onRefresh();
    void onDownload();
    void onDelete();
    void onOpenDir();
    void onBrowseDir();
    void onSaveDir();
    void onSelectionChanged();
    void onDownloadProgress(int percent, const QString& text);
    void onDownloadFinished(bool ok, const QString& info);

private:
    QTableWidget* m_table{nullptr};
    QPushButton* m_btnRefresh{nullptr};
    QPushButton* m_btnDownload{nullptr};
    QPushButton* m_btnDelete{nullptr};
    QPushButton* m_btnOpenDir{nullptr};
    // 模型目录设置
    QLineEdit* m_dirEdit{nullptr};
    QPushButton* m_btnBrowseDir{nullptr};
    QPushButton* m_btnSaveDir{nullptr};
    // 下载状态与进度
    QLabel* m_statusLabel{nullptr};
    QProgressBar* m_progress{nullptr};
    QThread* m_dlThread{nullptr};
};