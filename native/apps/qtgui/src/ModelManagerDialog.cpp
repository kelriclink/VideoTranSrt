#include "ModelManagerDialog.h"
#include "video2srt_native/model_manager.hpp"
#include "video2srt_native/config_manager.hpp"

#include <QMessageBox>
#include <QFileDialog>
#include <QDesktopServices>
#include <QUrl>
#include <QLineEdit>
#include <QLabel>
#include <QThread>
#include <QProgressBar>

// 后台下载 Worker：在 QThread 中运行，避免阻塞 GUI
class ModelDownloadWorker : public QObject {
    Q_OBJECT
public:
    explicit ModelDownloadWorker(QString size, QObject* parent = nullptr)
        : QObject(parent), m_size(std::move(size)) {}

public slots:
    void run() {
        // 进度回调：如果无法获取总长度，将 percent 设为 -1 表示不确定进度
        auto progress_cb = [this](const std::string& name, size_t done, size_t total) {
            Q_UNUSED(name);
            int pct = (total > 0) ? (int)((double)done / (double)total * 100.0) : -1;
            Q_EMIT progress(pct, QString("已下载 %1 / %2 字节").arg((qlonglong)done).arg((qlonglong)total));
        };
        bool ok = v2s::ModelManager::download_model(m_size.toUtf8().constData(), progress_cb);
        Q_EMIT finished(ok, ok ? QString("下载完成: %1").arg(m_size) : QString("下载失败: %1").arg(m_size));
    }

signals:
    void progress(int percent, const QString& text);
    void finished(bool ok, const QString& info);

private:
    QString m_size;
};

ModelManagerDialog::ModelManagerDialog(QWidget* parent)
    : QDialog(parent) {
    setupUi();
    refresh();
}

void ModelManagerDialog::setupUi() {
    setWindowTitle("模型管理");
    resize(700, 380);

    auto* layout = new QVBoxLayout(this);
    // 顶部：模型目录设置
    {
        auto* dirLayout = new QHBoxLayout();
        auto* dirLabel = new QLabel("模型目录:");
        m_dirEdit = new QLineEdit(this);
        m_btnBrowseDir = new QPushButton("浏览...", this);
        m_btnSaveDir = new QPushButton("保存", this);
        dirLayout->addWidget(dirLabel);
        dirLayout->addWidget(m_dirEdit);
        dirLayout->addWidget(m_btnBrowseDir);
        dirLayout->addWidget(m_btnSaveDir);
        layout->addLayout(dirLayout);
        connect(m_btnBrowseDir, &QPushButton::clicked, this, &ModelManagerDialog::onBrowseDir);
        connect(m_btnSaveDir, &QPushButton::clicked, this, &ModelManagerDialog::onSaveDir);
        // 启动时加载配置并回填
        v2s::ConfigManager::apply_model_dir_from_config(std::filesystem::path("config/config.json"), std::filesystem::path("config/default_config.json"));
        m_dirEdit->setText(QString::fromUtf8(v2s::ModelManager::get_model_dir().string().c_str()));
    }
    m_table = new QTableWidget(this);
    m_table->setColumnCount(5);
    QStringList headers; headers << "模型" << "大小" << "状态" << "文件大小" << "路径";
    m_table->setHorizontalHeaderLabels(headers);
    m_table->horizontalHeader()->setStretchLastSection(true);
    m_table->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_table->setSelectionMode(QAbstractItemView::SingleSelection);
    layout->addWidget(m_table);
    // 选中状态与下载进度
    m_statusLabel = new QLabel("状态: 空闲", this);
    m_progress = new QProgressBar(this);
    m_progress->setRange(0, 100);
    m_progress->setValue(0);
    auto* statusLayout = new QHBoxLayout();
    statusLayout->addWidget(m_statusLabel);
    statusLayout->addWidget(m_progress);
    layout->addLayout(statusLayout);

    auto* btns = new QHBoxLayout();
    m_btnRefresh = new QPushButton("刷新"); btns->addWidget(m_btnRefresh);
    m_btnDownload = new QPushButton("下载选中"); btns->addWidget(m_btnDownload);
    m_btnDelete = new QPushButton("删除选中"); btns->addWidget(m_btnDelete);
    m_btnOpenDir = new QPushButton("打开目录"); btns->addWidget(m_btnOpenDir);
    btns->addStretch();
    layout->addLayout(btns);

    connect(m_btnRefresh, &QPushButton::clicked, this, &ModelManagerDialog::onRefresh);
    connect(m_btnDownload, &QPushButton::clicked, this, &ModelManagerDialog::onDownload);
    connect(m_btnDelete, &QPushButton::clicked, this, &ModelManagerDialog::onDelete);
    connect(m_btnOpenDir, &QPushButton::clicked, this, &ModelManagerDialog::onOpenDir);
    connect(m_table, &QTableWidget::itemSelectionChanged, this, &ModelManagerDialog::onSelectionChanged);
}

void ModelManagerDialog::refresh() {
    auto infos = v2s::ModelManager::list_models();
    m_table->setRowCount(static_cast<int>(infos.size()));
    for (int i = 0; i < static_cast<int>(infos.size()); ++i) {
        const auto& info = infos[i];
        m_table->setItem(i, 0, new QTableWidgetItem(QString::fromUtf8(info.name.c_str())));
        m_table->setItem(i, 1, new QTableWidgetItem(QString::fromUtf8(info.size.c_str())));
        m_table->setItem(i, 2, new QTableWidgetItem(info.is_downloaded ? "已下载" : "未下载"));
        QString fileSizeStr = "-";
        if (info.is_downloaded && info.file_size.has_value()) {
            fileSizeStr = QString::number(static_cast<qlonglong>(info.file_size.value()));
        }
        m_table->setItem(i, 3, new QTableWidgetItem(fileSizeStr));
        auto path = v2s::ModelManager::get_model_file_path(info.size);
        m_table->setItem(i, 4, new QTableWidgetItem(QString::fromUtf8(path.string().c_str())));
    }
}

int ModelManagerDialog::selectedRow() const {
    auto ranges = m_table->selectedRanges();
    if (ranges.isEmpty()) return -1;
    return ranges.first().topRow();
}

void ModelManagerDialog::onRefresh() { refresh(); }

void ModelManagerDialog::onDownload() {
    int row = selectedRow();
    if (row < 0) { QMessageBox::warning(this, "提示", "请选择一行"); return; }
    QString size = m_table->item(row, 1)->text();
    // 已下载则避免重复下载
    if (m_table->item(row, 2)->text() == "已下载") {
        QMessageBox::information(this, "提示", QString("模型 %1 已存在，无需下载").arg(size));
        return;
    }

    // 禁用操作控件，仅保留取消对话框功能
    m_btnRefresh->setEnabled(false);
    m_btnDownload->setEnabled(false);
    m_btnDelete->setEnabled(false);
    m_btnOpenDir->setEnabled(false);
    m_btnBrowseDir->setEnabled(false);
    m_btnSaveDir->setEnabled(false);
    m_progress->setRange(0, 100);
    m_progress->setValue(0);
    setWindowTitle("模型管理 - 下载中...");
    m_statusLabel->setText(QString("正在下载: %1 到目录 %2").arg(size).arg(QString::fromUtf8(v2s::ModelManager::get_model_dir().string().c_str())));

    // 启动后台线程
    m_dlThread = new QThread(this);
    auto* worker = new ModelDownloadWorker(size);
    worker->moveToThread(m_dlThread);
    connect(m_dlThread, &QThread::started, worker, &ModelDownloadWorker::run);
    connect(worker, &ModelDownloadWorker::progress, this, &ModelManagerDialog::onDownloadProgress, Qt::QueuedConnection);
    connect(worker, &ModelDownloadWorker::finished, this, &ModelManagerDialog::onDownloadFinished, Qt::QueuedConnection);
    connect(worker, &ModelDownloadWorker::finished, m_dlThread, &QThread::quit);
    connect(m_dlThread, &QThread::finished, worker, &QObject::deleteLater);
    connect(m_dlThread, &QThread::finished, m_dlThread, &QObject::deleteLater);
    m_dlThread->start();
}

void ModelManagerDialog::onDelete() {
    int row = selectedRow();
    if (row < 0) { QMessageBox::warning(this, "提示", "请选择一行"); return; }
    QString size = m_table->item(row, 1)->text();
    auto ret = QMessageBox::question(this, "确认", QString("确认删除模型 %1 ?").arg(size));
    if (ret == QMessageBox::Yes) {
        bool ok = v2s::ModelManager::delete_model(size.toUtf8().constData());
        QMessageBox::information(this, ok ? "成功" : "失败", ok ? "删除完成" : "删除失败或不存在");
        refresh();
    }
}

void ModelManagerDialog::onOpenDir() {
    auto dir = v2s::ModelManager::get_model_dir();
    QDesktopServices::openUrl(QUrl::fromLocalFile(QString::fromUtf8(dir.string().c_str())));
}

void ModelManagerDialog::onBrowseDir() {
    QString dir = QFileDialog::getExistingDirectory(this, "选择模型目录", QString::fromUtf8(v2s::ModelManager::get_model_dir().string().c_str()));
    if (!dir.isEmpty()) {
        m_dirEdit->setText(dir);
    }
}

void ModelManagerDialog::onSaveDir() {
    QString dir = m_dirEdit->text();
    if (dir.isEmpty()) {
        QMessageBox::warning(this, "提示", "请输入或选择模型目录");
        return;
    }
    // 应用到 ModelManager 并写入配置
    v2s::ModelManager::set_model_dir(std::filesystem::path(dir.toUtf8().constData()));
    if (!v2s::ConfigManager::save_model_dir_to_config(std::filesystem::path("config/config.json"), std::filesystem::path("config/default_config.json"), std::filesystem::path(dir.toUtf8().constData()))) {
        QMessageBox::warning(this, "提示", "保存到配置文件失败");
    } else {
        QMessageBox::information(this, "成功", "模型目录已保存");
    }
    refresh();
}

void ModelManagerDialog::onSelectionChanged() {
    int row = selectedRow();
    if (row < 0) { m_statusLabel->setText("状态: 空闲"); return; }
    QString model = m_table->item(row, 0)->text();
    QString size = m_table->item(row, 1)->text();
    QString stat = m_table->item(row, 2)->text();
    m_statusLabel->setText(QString("当前选择: %1（大小: %2，状态: %3）").arg(model).arg(size).arg(stat));
}

void ModelManagerDialog::onDownloadProgress(int percent, const QString& text) {
    if (percent >= 0) {
        m_progress->setRange(0, 100);
        m_progress->setValue(percent);
        setWindowTitle(QString("模型管理 - 下载中 %1%").arg(percent));
    } else {
        // 不确定进度：显示活动条
        m_progress->setRange(0, 0);
        setWindowTitle("模型管理 - 下载中...");
    }
    m_statusLabel->setText(text);
}

void ModelManagerDialog::onDownloadFinished(bool ok, const QString& info) {
    // 恢复控件
    m_btnRefresh->setEnabled(true);
    m_btnDownload->setEnabled(true);
    m_btnDelete->setEnabled(true);
    m_btnOpenDir->setEnabled(true);
    m_btnBrowseDir->setEnabled(true);
    m_btnSaveDir->setEnabled(true);
    m_progress->setRange(0, 100);
    m_progress->setValue(0);
    setWindowTitle("模型管理");
    m_statusLabel->setText(info);
    refresh();
    QMessageBox::information(this, ok ? "成功" : "失败", ok ? "下载完成" : "下载失败");
}

// Worker 类在此 .cpp 中定义且包含 Q_OBJECT，需包含对应的 MOC 输出
#include "ModelManagerDialog.moc"