import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';

mermaid.initialize({ 
    startOnLoad: false,  // Changed to false for manual control
    theme: '{mermaid_theme}',
    securityLevel: 'loose',
    logLevel: 'debug',  // Changed to debug to see what's happening
    flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
    },
    sequence: {
        useMaxWidth: true,
        wrap: true
    },
    gantt: {
        useMaxWidth: true
    },
    er: {
        useMaxWidth: true
    },
    pie: {
        useMaxWidth: true
    },
    quadrantChart: {
        useMaxWidth: true
    },
    xyChart: {
        useMaxWidth: true
    },
    timeline: {
        useMaxWidth: true
    },
    mindmap: {
        useMaxWidth: true
    },
    gitGraph: {
        useMaxWidth: true
    },
    c4: {
        useMaxWidth: true
    },
    sankey: {
        useMaxWidth: true
    },
    block: {
        useMaxWidth: true
    }
});

// Render Mermaid diagrams - try multiple times to ensure rendering
async function renderMermaid() {
    try {
        const mermaidElements = document.querySelectorAll('.mermaid');
        console.log('Found mermaid elements:', mermaidElements.length);
        
        if (mermaidElements.length > 0) {
            mermaidElements.forEach(el => {
                console.log('Mermaid content:', el.textContent.substring(0, 100));
            });
            
            await mermaid.run({
                querySelector: '.mermaid'
            });
            console.log('Mermaid rendering complete');
        }
    } catch (error) {
        console.error('Mermaid rendering error:', error);
    }
}

// Try rendering on multiple events to ensure it works
window.addEventListener('DOMContentLoaded', renderMermaid);
window.addEventListener('load', renderMermaid);

// Also expose function globally in case we need to trigger it manually
window.renderMermaid = renderMermaid;