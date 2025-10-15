#pragma once

#include <QMainWindow>
#include <memory>

class QLineEdit;
class QComboBox;
class QCheckBox;
class QSpinBox;
class QDoubleSpinBox;
class QProgressBar;
class QPlainTextEdit;
class QPushButton;
class QLabel;
class QDialog;

class ModelManagerDialog;

namespace v2s {
    struct ProcessingResult;
    struct ProcessingConfig;
}

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void onBrowseInput();
    void onBrowseOutput();
    void onStart();
    void onFormatChanged(int);

    // 后台线程回调到 UI
    void onProgress(const QString &stage, double progress, const QString &message);
    void onFinished(bool ok, const QString &info);

private:
    void setupUi();
    void loadLanguages();
    void setControlsEnabled(bool enabled);
    QString generateOutputPath(const QString &inputPath, bool audioOnly, const QString &fmt) const;

    // UI 控件
    QLineEdit *m_inputEdit;
    QPushButton *m_inputBrowseBtn;
    QLineEdit *m_outputEdit;
    QPushButton *m_outputBrowseBtn;
    QComboBox *m_formatCombo;
    QComboBox *m_languageCombo;
    QComboBox *m_targetLanguageCombo;
    QComboBox *m_modelCombo;
    QCheckBox *m_gpuCheck;
    QSpinBox *m_threadsSpin;
    QCheckBox *m_mergeCheck;
    QCheckBox *m_bilingualCheck;
    QCheckBox *m_audioOnlyCheck;
    QPushButton *m_modelManageBtn;
    QPushButton *m_startBtn;
    QProgressBar *m_progressBar;
    QPlainTextEdit *m_logEdit;

    // 翻译器相关控件
    QComboBox *m_translatorCombo;
    QLabel *m_translatorStatusLabel;
    QPushButton *m_testTranslatorBtn;
    // 通用选项
    QSpinBox *m_translatorTimeoutSpin;
    QSpinBox *m_translatorRetrySpin;
    QCheckBox *m_translatorSslBypassCheck;
    // OpenAI 专用选项
    QLineEdit *m_openaiApiKeyEdit;
    QLineEdit *m_openaiBaseUrlEdit;
    QLineEdit *m_openaiModelEdit;
    QSpinBox *m_openaiMaxTokensSpin;
    QDoubleSpinBox *m_openaiTemperatureSpin;

    // OpenAI 相关标签（用于安全控制显示/隐藏，避免通过 centralWidget 查找导致空指针）
    QLabel *m_lblOpenAIApiKey{nullptr};
    QLabel *m_lblOpenAIBaseUrl{nullptr};
    QLabel *m_lblOpenAIModel{nullptr};
    QLabel *m_lblOpenAIMaxTokens{nullptr};
    QLabel *m_lblOpenAITemperature{nullptr};

    // 线程状态
    bool m_processing{false};

private slots:
    void onManageModels();
    void onTranslatorChanged(int);
    void onTestTranslator();
};