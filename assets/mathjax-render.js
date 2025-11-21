window.addEventListener('load', () => {
    if (window.MathJax) {
        MathJax.typesetPromise().catch((err) => console.log('MathJax error:', err));
    }
});