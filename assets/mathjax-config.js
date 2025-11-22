window.MathJax = {
    tex: {
        inlineMath: [['$', '$'], ['\\(', '\\)']], 
        displayMath: [['$$', '$$'], ['\\[', '\\]']],
        processEscapes: true,
        processEnvironments: true,
        packages: {'[+]': ['ams', 'newcommand', 'configmacros', 'action', 'unicode']},
        tags: 'ams',
        macros: {
            RR: '{\\mathbb{R}}',
            NN: '{\\mathbb{N}}',
            ZZ: '{\\mathbb{Z}}',
            QQ: '{\\mathbb{Q}}',
            CC: '{\\mathbb{C}}'
        }
    },
    svg: {
        fontCache: 'global'
    },
    options: {
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
        ignoreHtmlClass: 'no-mathjax'
    },
    startup: {
        pageReady: () => {
            return MathJax.startup.defaultPageReady();
        }
    }
};