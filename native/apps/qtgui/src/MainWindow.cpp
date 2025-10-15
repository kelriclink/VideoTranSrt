#include "MainWindow.h"

#include <QApplication>
#include <QFileDialog>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QFormLayout>
#include <QLineEdit>
#include <QComboBox>
#include <QCheckBox>
#include <QSpinBox>
#include <QDoubleSpinBox>
#include <QProgressBar>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QMessageBox>
#include <QThread>
#include <QLabel>
#include <QGroupBox>

#include <atomic>
#include <thread>
#include <sstream>
#include <filesystem>

#include "video2srt_native/processor.hpp"
#include "video2srt_native/config_manager.hpp"
#include "video2srt_native/core.hpp"
#include "video2srt_native/transcriber.hpp"
#include "video2srt_native/model_manager.hpp"
#include "video2srt_native/translator.hpp"

#include "ModelManagerDialog.h"

// Worker 对象在后台线程中运行，负责调用 v2s::Processor
class Worker : public QObject {
    Q_OBJECT
public:
    explicit Worker(v2s::ProcessingConfig cfg, bool audioOnly, QObject *parent = nullptr)
        : QObject(parent), m_cfg(std::move(cfg)), m_audioOnly(audioOnly) {}

public slots:
    void run() {
        v2s::Processor processor(m_cfg);
        auto progress_cb = [this](const std::string &stage, double prog, const std::string &message) {
            Q_EMIT progress(QString::fromUtf8(stage.c_str()), prog, QString::fromUtf8(message.c_str()));
        };

        if (m_audioOnly) {
            bool ok = processor.extract_audio_only(m_cfg.input_path, m_cfg.output_path, progress_cb);
            Q_EMIT finished(ok, QString::fromUtf8(ok ? (std::string("完成: ") + m_cfg.output_path).c_str()
                                                    : "音频提取失败"));
        } else {
            v2s::ProcessingResult res = processor.process(m_cfg.input_path, m_cfg.output_path, progress_cb);
            Q_EMIT finished(res.success, QString::fromUtf8(res.success ? (std::string("完成: ") + res.output_path).c_str()
                                                                      : res.error_message.c_str()));
        }
    }

signals:
    void progress(const QString &stage, double progress, const QString &message);
    void finished(bool ok, const QString &info);

private:
    v2s::ProcessingConfig m_cfg;
    bool m_audioOnly{false};
};

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent) {
    setupUi();
    loadLanguages();
    // 启动时应用配置中的模型目录，确保 GUI 使用统一目录
    v2s::ConfigManager::apply_model_dir_from_config(std::filesystem::path("config/config.json"), std::filesystem::path("config/default_config.json"));
    // 读取配置到 UI（模型/语言/GPU/翻译器等）
    loadConfigToUi();
    setWindowTitle(QString::fromUtf8("Video2SRT Qt GUI ") + QString::fromUtf8(v2s::version().c_str()));
}

MainWindow::~MainWindow() = default;

void MainWindow::setupUi() {
    auto *central = new QWidget(this);
    auto *mainLayout = new QVBoxLayout(central);

    // 顶部表单
    auto *form = new QGridLayout();

    int row = 0;
    form->addWidget(new QLabel("输入文件:"), row, 0);
    m_inputEdit = new QLineEdit; form->addWidget(m_inputEdit, row, 1);
    m_inputBrowseBtn = new QPushButton("浏览..."); form->addWidget(m_inputBrowseBtn, row, 2);
    connect(m_inputBrowseBtn, &QPushButton::clicked, this, &MainWindow::onBrowseInput);
    row++;

    form->addWidget(new QLabel("输出文件:"), row, 0);
    m_outputEdit = new QLineEdit; form->addWidget(m_outputEdit, row, 1);
    m_outputBrowseBtn = new QPushButton("另存为..."); form->addWidget(m_outputBrowseBtn, row, 2);
    connect(m_outputBrowseBtn, &QPushButton::clicked, this, &MainWindow::onBrowseOutput);
    row++;

    form->addWidget(new QLabel("输出格式:"), row, 0);
    m_formatCombo = new QComboBox; m_formatCombo->addItems({"srt","vtt","ass"});
    form->addWidget(m_formatCombo, row, 1);
    connect(m_formatCombo, qOverload<int>(&QComboBox::currentIndexChanged), this, &MainWindow::onFormatChanged);

    m_languageCombo = new QComboBox; m_languageCombo->addItem("auto");
    form->addWidget(new QLabel("语言:"), row, 2);
    form->addWidget(m_languageCombo, row, 3);

    m_modelCombo = new QComboBox;
    // 统一模型管理：从核心 ModelManager::list_models 动态获取列表
    try {
        auto infos = v2s::ModelManager::list_models();
        QStringList items;
        for (const auto &info : infos) {
            // 使用 info.size 作为可选项（例如 tiny、base.en、large-v3 等）
            items << QString::fromUtf8(info.size.c_str());
        }
        if (!items.isEmpty()) {
            m_modelCombo->addItems(items);
        } else {
            // 兜底：核心未返回时保留基本模型集合
            m_modelCombo->addItems({"tiny","base","small","medium","large-v3"});
        }
    } catch (...) {
        m_modelCombo->addItems({"tiny","base","small","medium","large-v3"});
    }
    form->addWidget(new QLabel("模型:"), row, 4);
    form->addWidget(m_modelCombo, row, 5);
    m_modelManageBtn = new QPushButton("管理模型...");
    form->addWidget(m_modelManageBtn, row, 6);
    connect(m_modelManageBtn, &QPushButton::clicked, this, &MainWindow::onManageModels);
    row++;

    m_gpuCheck = new QCheckBox("GPU加速"); form->addWidget(m_gpuCheck, row, 0);
    form->addWidget(new QLabel("线程:"), row, 1);
    m_threadsSpin = new QSpinBox; m_threadsSpin->setRange(1, 64); m_threadsSpin->setValue(4); form->addWidget(m_threadsSpin, row, 2);
    m_mergeCheck = new QCheckBox("合并片段"); form->addWidget(m_mergeCheck, row, 3);
    m_bilingualCheck = new QCheckBox("双语字幕"); form->addWidget(m_bilingualCheck, row, 4);
    m_audioOnlyCheck = new QCheckBox("仅音频"); form->addWidget(m_audioOnlyCheck, row, 5);
    row++;

    m_startBtn = new QPushButton("开始转换");
    form->addWidget(m_startBtn, row, 0);
    connect(m_startBtn, &QPushButton::clicked, this, &MainWindow::onStart);

    m_progressBar = new QProgressBar; m_progressBar->setRange(0, 100); m_progressBar->setValue(0);
    form->addWidget(m_progressBar, row, 1, 1, 3);
    row++;

    mainLayout->addLayout(form);

    // 翻译器设置区域
    auto *translatorGroup = new QGroupBox("翻译设置");
    auto *tgrid = new QGridLayout(translatorGroup);

    int trow = 0;
    tgrid->addWidget(new QLabel("翻译器:"), trow, 0);
    m_translatorCombo = new QComboBox; 
    m_translatorCombo->addItems({"不翻译", "simple", "google", "openai"});
    tgrid->addWidget(m_translatorCombo, trow, 1);
    connect(m_translatorCombo, qOverload<int>(&QComboBox::currentIndexChanged), this, &MainWindow::onTranslatorChanged);

    tgrid->addWidget(new QLabel("目标语言:"), trow, 2);
    m_targetLanguageCombo = new QComboBox; 
    m_targetLanguageCombo->addItem("不翻译"); // 后续由 loadLanguages() 填充
    tgrid->addWidget(m_targetLanguageCombo, trow, 3);
    trow++;

    // 通用选项（超时/重试/SSL绕过）
    tgrid->addWidget(new QLabel("超时(秒):"), trow, 0);
    m_translatorTimeoutSpin = new QSpinBox; m_translatorTimeoutSpin->setRange(1, 120); m_translatorTimeoutSpin->setValue(15);
    tgrid->addWidget(m_translatorTimeoutSpin, trow, 1);

    tgrid->addWidget(new QLabel("重试次数:"), trow, 2);
    m_translatorRetrySpin = new QSpinBox; m_translatorRetrySpin->setRange(0, 10); m_translatorRetrySpin->setValue(3);
    tgrid->addWidget(m_translatorRetrySpin, trow, 3);
    trow++;

    m_translatorSslBypassCheck = new QCheckBox("忽略SSL证书错误(不推荐)");
    tgrid->addWidget(m_translatorSslBypassCheck, trow, 0, 1, 4);
    trow++;

    // OpenAI 选项
    m_lblOpenAIApiKey = new QLabel("OpenAI API Key:");
    tgrid->addWidget(m_lblOpenAIApiKey, trow, 0);
    m_openaiApiKeyEdit = new QLineEdit; tgrid->addWidget(m_openaiApiKeyEdit, trow, 1, 1, 3);
    trow++;

    m_lblOpenAIBaseUrl = new QLabel("Base URL:");
    tgrid->addWidget(m_lblOpenAIBaseUrl, trow, 0);
    m_openaiBaseUrlEdit = new QLineEdit; m_openaiBaseUrlEdit->setText("https://api.openai.com/v1");
    tgrid->addWidget(m_openaiBaseUrlEdit, trow, 1, 1, 3);
    trow++;

    m_lblOpenAIModel = new QLabel("模型:");
    tgrid->addWidget(m_lblOpenAIModel, trow, 0);
    m_openaiModelEdit = new QLineEdit; m_openaiModelEdit->setText("gpt-4o-mini");
    tgrid->addWidget(m_openaiModelEdit, trow, 1);

    m_lblOpenAIMaxTokens = new QLabel("Max Tokens:");
    tgrid->addWidget(m_lblOpenAIMaxTokens, trow, 2);
    m_openaiMaxTokensSpin = new QSpinBox; m_openaiMaxTokensSpin->setRange(256, 16000); m_openaiMaxTokensSpin->setValue(4000);
    tgrid->addWidget(m_openaiMaxTokensSpin, trow, 3);
    trow++;

    m_lblOpenAITemperature = new QLabel("Temperature:");
    tgrid->addWidget(m_lblOpenAITemperature, trow, 0);
    m_openaiTemperatureSpin = new QDoubleSpinBox; m_openaiTemperatureSpin->setRange(0.0, 2.0); m_openaiTemperatureSpin->setSingleStep(0.1); m_openaiTemperatureSpin->setValue(0.3);
    tgrid->addWidget(m_openaiTemperatureSpin, trow, 1);
    trow++;

    // 状态与测试
    m_translatorStatusLabel = new QLabel("状态: 未测试");
    tgrid->addWidget(m_translatorStatusLabel, trow, 0, 1, 2);
    m_testTranslatorBtn = new QPushButton("测试翻译器");
    tgrid->addWidget(m_testTranslatorBtn, trow, 2, 1, 2);
    connect(m_testTranslatorBtn, &QPushButton::clicked, this, &MainWindow::onTestTranslator);
    trow++;

    // 保存配置按钮
    m_saveConfigBtn = new QPushButton("保存配置");
    tgrid->addWidget(m_saveConfigBtn, trow, 0, 1, 2);
    connect(m_saveConfigBtn, &QPushButton::clicked, this, &MainWindow::onSaveConfig);
    auto *lblSaveHint = new QLabel("保存到 config/config.json");
    tgrid->addWidget(lblSaveHint, trow, 2, 1, 2);
    trow++;

    // 初始隐藏 OpenAI 相关选项（当选择 openai 时显示）
    onTranslatorChanged(m_translatorCombo->currentIndex());

    mainLayout->addWidget(translatorGroup);

    // 日志区域
    auto *logLabel = new QLabel("日志:");
    mainLayout->addWidget(logLabel);
    m_logEdit = new QPlainTextEdit; m_logEdit->setReadOnly(true); m_logEdit->setMinimumHeight(300);
    mainLayout->addWidget(m_logEdit);

    central->setLayout(mainLayout);
    setCentralWidget(central);
}

void MainWindow::loadConfigToUi() {
    // 优先读取用户配置，失败则回退到默认配置
    v2s::ProcessingConfig cfg;
    bool ok = v2s::ConfigManager::apply_default_config(cfg, std::filesystem::path("config/config.json"));
    if (!ok) {
        v2s::ConfigManager::apply_default_config(cfg, std::filesystem::path("config/default_config.json"));
    }

    // 模型
    if (!cfg.model_size.empty()) {
        const QString qModel = QString::fromUtf8(cfg.model_size.c_str());
        int idx = m_modelCombo->findText(qModel, Qt::MatchExactly);
        if (idx >= 0) m_modelCombo->setCurrentIndex(idx);
    }

    // 语言（为空或 auto 则保持 "auto"）
    QString qLang = QString("auto");
    if (cfg.language.has_value() && !cfg.language->empty()) {
        qLang = QString::fromUtf8(cfg.language->c_str());
    }
    int langIdx = m_languageCombo->findText(qLang, Qt::MatchExactly);
    if (langIdx >= 0) m_languageCombo->setCurrentIndex(langIdx);
    else m_languageCombo->setCurrentText(QString("auto"));

    // GPU 选项（优先根据 device，其次根据 use_gpu 布尔值）
    if (!cfg.device.empty()) {
        if (cfg.device == "cuda" || cfg.device == "gpu") {
            m_gpuCheck->setChecked(true);
        } else if (cfg.device == "cpu") {
            m_gpuCheck->setChecked(false);
        }
    } else {
        m_gpuCheck->setChecked(cfg.use_gpu);
    }

    // 翻译器类型：offline/simple 显示为“ 不翻译 ”；google/openai 显示对应选项
    std::string type = cfg.translator_type;
    if (type == "offline" || type == "simple" || type.empty()) {
        int tIdx = m_translatorCombo->findText(QString("不翻译"), Qt::MatchExactly);
        if (tIdx >= 0) m_translatorCombo->setCurrentIndex(tIdx);
    } else {
        const QString qType = QString::fromUtf8(type.c_str());
        int tIdx = m_translatorCombo->findText(qType, Qt::MatchExactly);
        if (tIdx >= 0) m_translatorCombo->setCurrentIndex(tIdx);
    }
    // 根据当前翻译器类型刷新可见性
    onTranslatorChanged(m_translatorCombo->currentIndex());

    // 通用翻译选项
    if (cfg.translator_options.timeout_seconds > 0) {
        m_translatorTimeoutSpin->setValue(cfg.translator_options.timeout_seconds);
    }
    m_translatorRetrySpin->setValue(cfg.translator_options.retry_count);
    m_translatorSslBypassCheck->setChecked(cfg.translator_options.ssl_bypass);

    // OpenAI 专用选项
    if (type == "openai") {
        m_openaiApiKeyEdit->setText(QString::fromUtf8(cfg.translator_options.api_key.c_str()));
        if (!cfg.translator_options.base_url.empty()) {
            m_openaiBaseUrlEdit->setText(QString::fromUtf8(cfg.translator_options.base_url.c_str()));
        }
        if (!cfg.translator_options.model.empty()) {
            m_openaiModelEdit->setText(QString::fromUtf8(cfg.translator_options.model.c_str()));
        }
        if (cfg.translator_options.max_tokens > 0) {
            m_openaiMaxTokensSpin->setValue(cfg.translator_options.max_tokens);
        }
        m_openaiTemperatureSpin->setValue(cfg.translator_options.temperature);
    }

    // 日志提示
    if (m_logEdit) {
        m_logEdit->appendPlainText(ok ? QString::fromUtf8("已从 config/config.json 读取配置并应用到界面")
                                      : QString::fromUtf8("未找到用户配置，已使用 default_config.json 初始化界面"));
    }
}

void MainWindow::loadLanguages() {
    try {
        if (v2s::Transcriber::is_available()) {
            auto langs = v2s::Transcriber::get_supported_languages();
            if (!langs.empty()) {
                for (const auto &l : langs) {
                    QString ql = QString::fromUtf8(l.c_str());
                    m_languageCombo->addItem(ql);
                    m_targetLanguageCombo->addItem(ql);
                }
            }
        }
    } catch (...) {
        // 忽略加载失败
    }
}

void MainWindow::setControlsEnabled(bool enabled) {
    m_inputEdit->setEnabled(enabled);
    m_inputBrowseBtn->setEnabled(enabled);
    m_outputEdit->setEnabled(enabled);
    m_outputBrowseBtn->setEnabled(enabled);
    m_formatCombo->setEnabled(enabled);
    m_languageCombo->setEnabled(enabled);
    m_modelCombo->setEnabled(enabled);
    m_gpuCheck->setEnabled(enabled);
    m_threadsSpin->setEnabled(enabled);
    m_mergeCheck->setEnabled(enabled);
    m_bilingualCheck->setEnabled(enabled);
    m_audioOnlyCheck->setEnabled(enabled);
    m_startBtn->setEnabled(enabled);
    // 翻译器相关控件
    m_translatorCombo->setEnabled(enabled);
    m_targetLanguageCombo->setEnabled(enabled);
    m_translatorTimeoutSpin->setEnabled(enabled);
    m_translatorRetrySpin->setEnabled(enabled);
    m_translatorSslBypassCheck->setEnabled(enabled);
    m_openaiApiKeyEdit->setEnabled(enabled);
    m_openaiBaseUrlEdit->setEnabled(enabled);
    m_openaiModelEdit->setEnabled(enabled);
    m_openaiMaxTokensSpin->setEnabled(enabled);
    m_openaiTemperatureSpin->setEnabled(enabled);
    m_testTranslatorBtn->setEnabled(enabled);
}

QString MainWindow::generateOutputPath(const QString &inputPath, bool audioOnly, const QString &fmt) const {
    std::filesystem::path in = std::filesystem::path(inputPath.toUtf8().constData());
    std::filesystem::path out = in.parent_path() / in.stem();
    if (audioOnly) out += ".wav";
    else if (fmt == "vtt") out += ".vtt";
    else if (fmt == "ass") out += ".ass";
    else out += ".srt";
    return QString::fromUtf8(out.string().c_str());
}

void MainWindow::onBrowseInput() {
    // 获取支持的格式
    QStringList filters;
    try {
        auto fmts = v2s::Processor::get_supported_formats();
        if (!fmts.empty()) {
            QString pattern;
            for (size_t i = 0; i < fmts.size(); ++i) {
                QString ext = QString::fromUtf8(fmts[i].c_str());
                // fmts 中已包含前导点，如 ".mp4"，这里直接拼接 "*" + ext 以避免出现 "*..mp4" 的错误
                if (!ext.startsWith('.')) {
                    ext = "." + ext; // 兜底，确保有前导点
                }
                pattern += "*" + ext;
                if (i + 1 < fmts.size()) pattern += " "; // Qt 过滤模式使用空格分隔
            }
            filters << (QString::fromUtf8("视频/音频文件 (") + pattern + ")");
        }
    } catch (...) {}
    if (filters.isEmpty()) filters << "视频/音频文件 (*.mp4 *.mkv *.mov *.avi *.wmv *.flv *.webm *.m4v *.mp3 *.wav *.flac)";
    // 增加通配的“所有文件”选项，便于用户在列表之外选择
    filters << "所有文件 (*)";

    QString file = QFileDialog::getOpenFileName(this, "选择输入文件", QString(), filters.join(";;"));
    if (!file.isEmpty()) {
        m_inputEdit->setText(file);
        bool audioOnly = m_audioOnlyCheck->isChecked();
        QString fmt = m_formatCombo->currentText();
        m_outputEdit->setText(generateOutputPath(file, audioOnly, fmt));
    }
}

void MainWindow::onBrowseOutput() {
    bool audioOnly = m_audioOnlyCheck->isChecked();
    QString fmt = m_formatCombo->currentText();
    QString filter;
    if (audioOnly) filter = "音频文件 (*.wav)";
    else if (fmt == "vtt") filter = "字幕文件 (*.vtt)";
    else if (fmt == "ass") filter = "字幕文件 (*.ass)";
    else filter = "字幕文件 (*.srt)";
    QString file = QFileDialog::getSaveFileName(this, "选择输出文件", QString(), filter + ";;所有文件 (*.*)");
    if (!file.isEmpty()) m_outputEdit->setText(file);
}

void MainWindow::onFormatChanged(int) {
    QString in = m_inputEdit->text();
    if (!in.isEmpty()) {
        bool audioOnly = m_audioOnlyCheck->isChecked();
        QString fmt = m_formatCombo->currentText();
        m_outputEdit->setText(generateOutputPath(in, audioOnly, fmt));
    }
}

void MainWindow::onStart() {
    if (m_processing) return;

    QString input = m_inputEdit->text();
    QString output = m_outputEdit->text();
    QString fmt = m_formatCombo->currentText();
    QString lang = m_languageCombo->currentText();
    QString model = m_modelCombo->currentText();
    bool gpu = m_gpuCheck->isChecked();
    bool merge = m_mergeCheck->isChecked();
    bool bilingual = m_bilingualCheck->isChecked();
    bool audioOnly = m_audioOnlyCheck->isChecked();
    int threads = m_threadsSpin->value();

    if (input.isEmpty()) { QMessageBox::warning(this, "提示", "请先选择输入文件"); return; }
    if (output.isEmpty()) { output = generateOutputPath(input, audioOnly, fmt); m_outputEdit->setText(output); }

    v2s::ProcessingConfig cfg;
    cfg.input_path = input.toUtf8().constData();
    cfg.output_path = output.toUtf8().constData();
    cfg.output_format = fmt.toUtf8().constData();
    cfg.model_size = model.toUtf8().constData();
    cfg.use_gpu = gpu;
    cfg.cpu_threads = threads;
    cfg.merge_segments = merge;
    cfg.bilingual = bilingual;
    if (lang != "auto" && !lang.isEmpty()) cfg.language = lang.toUtf8().constData(); else cfg.language = std::nullopt;

    // 翻译器配置
    QString translatorType = m_translatorCombo->currentText();
    QString targetLang = m_targetLanguageCombo->currentText();
    if (translatorType == "不翻译" || targetLang == "不翻译") {
        cfg.translate_to = std::nullopt;
        cfg.translator_type = "simple"; // 保持 simple，确保管线连通
    } else {
        cfg.translate_to = targetLang.toUtf8().constData();
        cfg.translator_type = translatorType.toUtf8().constData();
        // 通用选项
        cfg.translator_options.timeout_seconds = m_translatorTimeoutSpin->value();
        cfg.translator_options.retry_count = m_translatorRetrySpin->value();
        cfg.translator_options.ssl_bypass = m_translatorSslBypassCheck->isChecked();
        // OpenAI 专用选项
        if (translatorType == "openai") {
            cfg.translator_options.api_key = m_openaiApiKeyEdit->text().toUtf8().constData();
            cfg.translator_options.base_url = m_openaiBaseUrlEdit->text().toUtf8().constData();
            cfg.translator_options.model = m_openaiModelEdit->text().toUtf8().constData();
            cfg.translator_options.max_tokens = m_openaiMaxTokensSpin->value();
            cfg.translator_options.temperature = m_openaiTemperatureSpin->value();
        }
    }

    if (!v2s::ConfigManager::apply_default_config(cfg, std::filesystem::path("config/config.json"))) {
        v2s::ConfigManager::apply_default_config(cfg);
    }

    setControlsEnabled(false);
    m_processing = true;
    m_progressBar->setValue(0);
    m_logEdit->appendPlainText("开始处理...");

    // 创建线程与 worker
    auto *thread = new QThread(this);
    auto *worker = new Worker(cfg, audioOnly);
    worker->moveToThread(thread);
    connect(thread, &QThread::started, worker, &Worker::run);
    connect(worker, &Worker::progress, this, &MainWindow::onProgress, Qt::QueuedConnection);
    connect(worker, &Worker::finished, this, &MainWindow::onFinished, Qt::QueuedConnection);
    connect(worker, &Worker::finished, thread, &QThread::quit);
    connect(thread, &QThread::finished, worker, &QObject::deleteLater);
    connect(thread, &QThread::finished, thread, &QObject::deleteLater);
    thread->start();
}

void MainWindow::onProgress(const QString &stage, double progress, const QString &message) {
    int percent = qBound(0, static_cast<int>(progress * 100.0), 100);
    m_progressBar->setValue(percent);
    m_logEdit->appendPlainText(QString("[%1] %2% %3").arg(stage).arg(percent).arg(message));
}

void MainWindow::onFinished(bool ok, const QString &info) {
    m_processing = false;
    setControlsEnabled(true);
    m_logEdit->appendPlainText(info);
    QMessageBox::information(this, ok ? "成功" : "失败", ok ? "处理完成" : "处理失败");
}

void MainWindow::onManageModels() {
    ModelManagerDialog dlg(this);
    dlg.exec();
}

void MainWindow::onTranslatorChanged(int index) {
    Q_UNUSED(index);
    const QString type = m_translatorCombo->currentText();
    const bool isOpenAI = (type == "openai");
    const bool isGoogle = (type == "google");
    // 显示/隐藏 OpenAI 相关字段（包含标签和编辑框），避免通过 centralWidget 查找，防止启动阶段空指针导致崩溃
    if (m_lblOpenAIApiKey) m_lblOpenAIApiKey->setVisible(isOpenAI);
    if (m_lblOpenAIBaseUrl) m_lblOpenAIBaseUrl->setVisible(isOpenAI);
    if (m_lblOpenAIModel) m_lblOpenAIModel->setVisible(isOpenAI);
    if (m_lblOpenAIMaxTokens) m_lblOpenAIMaxTokens->setVisible(isOpenAI);
    if (m_lblOpenAITemperature) m_lblOpenAITemperature->setVisible(isOpenAI);
    m_openaiApiKeyEdit->setVisible(isOpenAI);
    m_openaiBaseUrlEdit->setVisible(isOpenAI);
    m_openaiModelEdit->setVisible(isOpenAI);
    m_openaiMaxTokensSpin->setVisible(isOpenAI);
    m_openaiTemperatureSpin->setVisible(isOpenAI);

    // SSL 绕过仅对网络请求生效（Google/OpenAI），simple 时隐藏
    m_translatorSslBypassCheck->setVisible(isOpenAI || isGoogle);
}

void MainWindow::onTestTranslator() {
    const QString type = m_translatorCombo->currentText();
    const QString targetLang = m_targetLanguageCombo->currentText();
    if (type == "不翻译" || targetLang == "不翻译") {
        m_translatorStatusLabel->setText("状态: 未启用翻译");
        return;
    }

    v2s::TranslatorOptions opts;
    opts.timeout_seconds = m_translatorTimeoutSpin->value();
    opts.retry_count = m_translatorRetrySpin->value();
    opts.ssl_bypass = m_translatorSslBypassCheck->isChecked();
    if (type == "openai") {
        opts.api_key = m_openaiApiKeyEdit->text().toUtf8().constData();
        opts.base_url = m_openaiBaseUrlEdit->text().toUtf8().constData();
        opts.model = m_openaiModelEdit->text().toUtf8().constData();
        opts.max_tokens = m_openaiMaxTokensSpin->value();
        opts.temperature = m_openaiTemperatureSpin->value();
    }

    std::unique_ptr<v2s::ITranslator> translator = v2s::create_translator(type.toUtf8().constData(), opts);
    std::vector<v2s::Segment> segs;
    segs.emplace_back(0.0, 1.0, std::string("你好，世界！"));
    v2s::TranslationResult tr = translator->translate_segments(segs, targetLang.toUtf8().constData(), "auto");
    if (!tr.segments.empty()) {
        m_translatorStatusLabel->setText(QString("状态: 成功 -> %1").arg(QString::fromUtf8(tr.segments[0].text.c_str())));
    } else {
        m_translatorStatusLabel->setText("状态: 失败");
    }
}

void MainWindow::onSaveConfig() {
    // 采集当前 UI 设置到 ProcessingConfig
    v2s::ProcessingConfig cfg;
    // 输出格式/模型/语言/GPU/线程/合并/双语仅与保存范围相关的项采集（模型/语言/GPU）
    cfg.model_size = m_modelCombo->currentText().toUtf8().constData();
    const QString lang = m_languageCombo->currentText();
    if (lang != "auto" && !lang.isEmpty()) cfg.language = lang.toUtf8().constData(); else cfg.language = std::nullopt;
    cfg.use_gpu = m_gpuCheck->isChecked();

    // 翻译器配置
    const QString translatorType = m_translatorCombo->currentText();
    // 将“ 不翻译 ”映射为 simple，保持与核心一致
    if (translatorType == "不翻译") cfg.translator_type = std::string("simple");
    else cfg.translator_type = translatorType.toUtf8().constData();
    cfg.translator_options.timeout_seconds = m_translatorTimeoutSpin->value();
    cfg.translator_options.retry_count = m_translatorRetrySpin->value();
    cfg.translator_options.ssl_bypass = m_translatorSslBypassCheck->isChecked();
    if (translatorType == "openai") {
        cfg.translator_options.api_key = m_openaiApiKeyEdit->text().toUtf8().constData();
        cfg.translator_options.base_url = m_openaiBaseUrlEdit->text().toUtf8().constData();
        cfg.translator_options.model = m_openaiModelEdit->text().toUtf8().constData();
        cfg.translator_options.max_tokens = m_openaiMaxTokensSpin->value();
        cfg.translator_options.temperature = m_openaiTemperatureSpin->value();
    }

    const bool ok = v2s::ConfigManager::save_user_config(std::filesystem::path("config/config.json"),
                                                         std::filesystem::path("config/default_config.json"),
                                                         cfg);
    if (ok) {
        m_logEdit->appendPlainText("配置已保存到 config/config.json");
        QMessageBox::information(this, "已保存", "配置保存成功");
    } else {
        m_logEdit->appendPlainText("配置保存失败，详见日志");
        QMessageBox::warning(this, "保存失败", "无法写入配置文件");
    }
}

// Worker 类在此 .cpp 中定义且包含 Q_OBJECT，需包含对应的 MOC 输出
#include "MainWindow.moc"