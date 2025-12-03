/**
 * mathjax-setup.js
 * * This file is the complete, working configuration and renderer trigger.
 */

// 1. CONFIGURATION
window.MathJax = {
    loader: {
        // Loads extensions defined in your original config
        load: ['[tex]/physics', '[tex]/mhchem', '[tex]/color', '[tex]/cancel']
    },
    tex: {
        // Enables extensions and sets delimiters
        packages: {'[+]': ['physics', 'mhchem', 'color', 'cancel', 'ams','tensor']},
        inlineMath: [['$', '$'], ['\\(', '\\)']], 
        displayMath: [['$$', '$$'], ['\\[', '\\]']],
        
        processEscapes: true,
        processEnvironments: true,
        tags: 'ams',
        
        // Custom Macros (Includes \RR, \pdd, etc., which are correctly defined)
        macros: {
            pdd: ['\\pdv{#1}{#2}', 2],
            ddf: ['\\dv{#1}{#2}', 2],
            ii: '\\mathrm{i}',
            opH: '\\hat{H}',
            RR: '{\\mathbb{R}}', // This macro is correctly defined
            NN: '{\\mathbb{N}}',
            ZZ: '{\\mathbb{Z}}',
            QQ: '{\\mathbb{Q}}',
            CC: '{\\mathbb{C}}',
            d: '{\\mathrm{d}}',
            bold: ['{\\boldsymbol{#1}}', 1]
        }
    },
    svg: {
        fontCache: 'global',
        scale: 1,
        minScale: 0.5
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

// 2. DYNAMIC LIBRARY LOADER (Ensures config is set before loading the library)
(function() {
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js';
    script.async = true;
    document.head.appendChild(script);
})();

// 3. RENDER TRIGGER (From mathjax-render.js)
window.addEventListener('load', () => {
    if (window.MathJax) {
        MathJax.typesetPromise().catch((err) => console.log('MathJax error:', err));
    }
});