const I18N_CONFIG = {
    defaultLanguage: "id",
    storageKey: "pdfmaster_language",
    languagesFile: "./languages.json",
    localesPath: "./locales/"
};

let currentLanguage = null;
let currentTranslations = {};


async function loadLanguages() {
    const response = await fetch(I18N_CONFIG.languagesFile);

    if (!response.ok) {
        throw new Error("Gagal memuat daftar bahasa.");
    }

    return await response.json();
}


async function loadLanguage(languageCode) {

    const response = await fetch(
        `${I18N_CONFIG.localesPath}${languageCode}.json`
    );

    if (!response.ok) {
        throw new Error(
            `File bahasa ${languageCode}.json tidak ditemukan.`
        );
    }

    currentTranslations = await response.json();
    currentLanguage = languageCode;

    localStorage.setItem(
        I18N_CONFIG.storageKey,
        languageCode
    );

    applyTranslations();
    updateLanguageDirection();
    updateLanguageSelectors();

    document.dispatchEvent(
        new CustomEvent("languageChanged", {
            detail: {
                language: languageCode
            }
        })
    );
}


function translate(key, fallback = "") {

    const value = key
        .split(".")
        .reduce(
            (obj, part) => obj?.[part],
            currentTranslations
        );

    if (value === undefined || value === null) {
        return fallback || key;
    }

    return value;
}


function applyTranslations() {

    // Teks biasa
    document
        .querySelectorAll("[data-i18n]")
        .forEach(element => {

            const key = element.dataset.i18n;

            const translated = translate(
                key,
                element.textContent
            );

            element.textContent = translated;
        });


    // Placeholder input
    document
        .querySelectorAll("[data-i18n-placeholder]")
        .forEach(element => {

            const key =
                element.dataset.i18nPlaceholder;

            element.placeholder =
                translate(
                    key,
                    element.placeholder
                );
        });


    // Title
    document
        .querySelectorAll("[data-i18n-title]")
        .forEach(element => {

            const key =
                element.dataset.i18nTitle;

            element.title =
                translate(
                    key,
                    element.title
                );
        });


    // Aria-label
    document
        .querySelectorAll("[data-i18n-aria-label]")
        .forEach(element => {

            const key =
                element.dataset.i18nAriaLabel;

            element.setAttribute(
                "aria-label",
                translate(
                    key,
                    element.getAttribute("aria-label") || ""
                )
            );
        });


    // Value button/input
    document
        .querySelectorAll("[data-i18n-value]")
        .forEach(element => {

            const key =
                element.dataset.i18nValue;

            element.value =
                translate(
                    key,
                    element.value
                );
        });
}


function updateLanguageDirection() {

    const rtlLanguages = ["ar"];

    const direction =
        rtlLanguages.includes(currentLanguage)
            ? "rtl"
            : "ltr";

    document.documentElement.lang =
        currentLanguage;

    document.documentElement.dir =
        direction;

    document.body.classList.toggle(
        "rtl-language",
        direction === "rtl"
    );
}


function updateLanguageSelectors() {

    document
        .querySelectorAll(
            "[data-language-selector]"
        )
        .forEach(selector => {

            selector.value =
                currentLanguage;
        });


    document
        .querySelectorAll(
            "[data-language-current]"
        )
        .forEach(element => {

            element.textContent =
                currentLanguage;
        });
}


async function initI18n() {

    try {

        const languages =
            await loadLanguages();

        const savedLanguage =
            localStorage.getItem(
                I18N_CONFIG.storageKey
            );

        const browserLanguage =
            navigator.language
                ?.split("-")[0];

        const supportedLanguages =
            languages.map(
                language => language.code
            );

        let language =
            savedLanguage ||
            browserLanguage ||
            I18N_CONFIG.defaultLanguage;

        if (
            !supportedLanguages.includes(language)
        ) {
            language =
                I18N_CONFIG.defaultLanguage;
        }

        await loadLanguage(language);


        // Pasang event selector
        document
            .querySelectorAll(
                "[data-language-selector]"
            )
            .forEach(selector => {

                selector.addEventListener(
                    "change",
                    async event => {

                        const newLanguage =
                            event.target.value;

                        await loadLanguage(
                            newLanguage
                        );
                    }
                );
            });

    } catch (error) {

        console.error(
            "I18N ERROR:",
            error
        );
    }
}


window.I18N = {
    init: initI18n,
    loadLanguage,
    translate,
    getLanguage: () => currentLanguage
};


document.addEventListener(
    "DOMContentLoaded",
    initI18n
);
