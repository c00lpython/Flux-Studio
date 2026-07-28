// ============================================================
//  EDITOR - С ДРЕВОВИДНЫМ EXPLORER И АВТОСОХРАНЕНИЕМ
// ============================================================

class Editor {
    constructor() {
        // --- Состояние ---
        this.projectId = null;
        this.projectData = null;
        this.elements = [];
        this.pages = [];
        this.selectedElement = null;
        this.selectedPage = null;
        this.isLoading = false;
        this.updateInterval = null;
        this.dirty = false;
        this.lastSave = null;
        this.frameCount = 0;
        this.saveTimeout = null;

        // --- Canvas ---
        this.canvas = null;
        this.canvasObjects = {};

        // --- UI элементы ---
        this.els = {};

        // --- Инициализация ---
        this.init();
    }

    // ============================================================
    //  ИНИЦИАЛИЗАЦИЯ
    // ============================================================

    async init() {
        console.log('🎨 Editor initializing...');

        this.els = {
            progressBar: document.getElementById('progressBar'),
            progressFill: document.getElementById('progressFill'),
            progressLabel: document.getElementById('progressLabel'),
            explorerList: document.getElementById('explorerList'),
            editorTabs: document.getElementById('editorTabs'),
            paletteItems: document.getElementById('paletteItems'),
            propertyRows: document.getElementById('propertyRows'),
            terminalOutput: document.getElementById('terminalOutput'),
            canvas: document.getElementById('canvas'),
            viewport: document.getElementById('viewport'),
            canvasWrapper: document.getElementById('canvasWrapper'),
            zoomLevel: document.getElementById('zoomLevel'),
        };

        this.initCanvas();
        this.setupZoomPan();

        this.projectId = window.projectId || this.getProjectIdFromURL();
        console.log('📌 Project ID:', this.projectId || 'None');

        // Восстанавливаем состояние из localStorage
        this.restoreState();

        if (this.projectId) {
            await this.loadProject();
        } else {
            this.renderEmptyState();
        }

        this.setupEvents();
        this.startUpdateLoop();
        this.setupResize();
        this.setupBeforeUnload();

        console.log('✅ Editor ready!');
    }

    // ============================================================
    //  CANVAS
    // ============================================================

    initCanvas() {
        this.canvas = new fabric.Canvas('canvas', {
            width: 520,
            height: 720,
            backgroundColor: '#ffffff',
            selection: true,
            selectionColor: 'rgba(0, 122, 204, 0.1)',
            selectionBorderColor: '#007acc',
            selectionLineWidth: 1,
            renderOnAddRemove: true,
        });
        this.canvas.renderAll();
    }

    // ============================================================
    //  ZOOM/PAN
    // ============================================================

    setupZoomPan() {
        const viewport = this.els.viewport;
        const wrapper = this.els.canvasWrapper;
        const zoomLevel = this.els.zoomLevel;

        let scale = 1, posX = 0, posY = 0, isDragging = false, startX = 0, startY = 0;

        const updateTransform = () => {
            wrapper.style.transform = `translate(${posX}px, ${posY}px) scale(${scale})`;
            zoomLevel.textContent = Math.round(scale * 100) + '%';
        };

        viewport.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = Math.sign(e.deltaY) * -0.05;
            const newScale = Math.min(Math.max(0.2, scale + delta), 3);
            const rect = viewport.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            const ratio = 1 - newScale / scale;
            posX -= (mouseX - viewport.clientWidth / 2) * ratio;
            posY -= (mouseY - viewport.clientHeight / 2) * ratio;
            scale = newScale;
            updateTransform();
        }, { passive: false });

        viewport.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX - posX;
            startY = e.clientY - posY;
            viewport.style.cursor = 'grabbing';
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            posX = e.clientX - startX;
            posY = e.clientY - startY;
            updateTransform();
        });

        window.addEventListener('mouseup', () => {
            isDragging = false;
            viewport.style.cursor = 'grab';
        });

        document.getElementById('zoomInBtn').addEventListener('click', () => {
            const newScale = Math.min(3, scale + 0.1);
            const ratio = 1 - newScale / scale;
            posX -= (viewport.clientWidth / 2) * ratio;
            posY -= (viewport.clientHeight / 2) * ratio;
            scale = newScale;
            updateTransform();
        });

        document.getElementById('zoomOutBtn').addEventListener('click', () => {
            const newScale = Math.max(0.2, scale - 0.1);
            const ratio = 1 - newScale / scale;
            posX -= (viewport.clientWidth / 2) * ratio;
            posY -= (viewport.clientHeight / 2) * ratio;
            scale = newScale;
            updateTransform();
        });

        document.getElementById('resetViewBtn').addEventListener('click', () => {
            scale = 1; posX = 0; posY = 0;
            updateTransform();
        });

        this._zoomState = { scale, posX, posY, updateTransform };
    }

    // ============================================================
    //  RESIZE
    // ============================================================

    setupResize() {
        const resize = () => {
            const container = document.querySelector('.page-container');
            const rect = container.getBoundingClientRect();
            const padding = 40;
            const w = rect.width - padding * 2;
            const h = rect.height - padding * 2;
            if (w > 0 && h > 0) {
                this.canvas.setWidth(w);
                this.canvas.setHeight(h);
                this.canvas.renderAll();
            }
        };

        window.addEventListener('resize', resize);
        setTimeout(resize, 100);
    }

    // ============================================================
    //  ЗАГРУЗКА ПРОЕКТА
    // ============================================================

    getProjectIdFromURL() {
        const path = window.location.pathname;
        const match = path.match(/\/project\/(.+)/);
        return match ? match[1] : null;
    }

    async loadProject() {
        this.isLoading = true;
        this.showProgress(true);
        this.updateProgress(0, 'Loading project...');

        try {
            this.updateProgress(20, 'Fetching project data...');
            const response = await fetch(`/api/project/${this.projectId}`);
            if (!response.ok) throw new Error('Project not found');
            const data = await response.json();
            this.projectData = data;

            this.updateProgress(40, 'Loading pages...');
            this.pages = Object.keys(data.project?.pages || {});
            if (this.pages.length > 0) this.selectedPage = this.pages[0];

            this.updateProgress(60, 'Loading elements...');
            this.elements = this.parseElements(data);

            this.updateProgress(80, 'Rendering...');
            this.render();

            this.updateProgress(100, 'Ready! 🎉');
            this.logTerminal('✅ Project loaded successfully', 'success');

            // Восстанавливаем выбранный элемент
            this.restoreSelectedElement();

            setTimeout(() => {
                this.showProgress(false);
                this.isLoading = false;
            }, 500);

        } catch (error) {
            console.error('❌ Failed to load project:', error);
            this.updateProgress(0, '❌ Error loading project');
            this.logTerminal(`❌ Error: ${error.message}`, 'error');
            setTimeout(() => {
                this.showProgress(false);
                this.isLoading = false;
            }, 2000);
        }
    }

    parseElements(data) {
        const elements = [];
        const pages = data.project?.pages || {};

        for (const [pageName, pageData] of Object.entries(pages)) {
            const pageElements = pageData.elements || {};
            for (const [elemId, elemData] of Object.entries(pageElements)) {
                elements.push({
                    id: elemId,
                    page: pageName,
                    type: elemData.Type || 'Text',
                    content: elemData.content || '',
                    style: this.elementToCSS(elemData),
                    data: elemData,
                    x: parseInt(elemData.left) || 100,
                    y: parseInt(elemData.top) || 100,
                });
            }
        }

        return elements;
    }

    elementToCSS(elemData) {
        const cssMap = {
            color: 'color',
            font_size: 'font-size',
            font_weight: 'font-weight',
            font_family: 'font-family',
            background_color: 'background-color',
            padding: 'padding',
            margin: 'margin',
            border: 'border',
            border_radius: 'border-radius',
            width: 'width',
            height: 'height',
            position: 'position',
            left: 'left',
            top: 'top',
            display: 'display',
            text_align: 'text-align'
        };

        const parts = [];
        for (const [key, prop] of Object.entries(cssMap)) {
            if (elemData[key]) {
                parts.push(`${prop}:${elemData[key]}`);
            }
        }
        return parts.join(';');
    }

    // ============================================================
    //  PROGRESS BAR
    // ============================================================

    showProgress(show) {
        const bar = this.els.progressBar;
        if (show) {
            bar.classList.remove('animating-out');
            bar.classList.add('animating-in', 'show');
            bar.style.display = 'flex';
        } else {
            bar.classList.remove('animating-in');
            bar.classList.add('animating-out');
            setTimeout(() => {
                bar.classList.remove('show', 'animating-out');
                bar.style.display = 'none';
            }, 400);
        }
    }

    updateProgress(percent, text) {
        const fill = this.els.progressFill;
        const label = this.els.progressLabel;
        if (fill) fill.style.width = percent + '%';
        if (label) label.textContent = text || `${percent}%`;
    }

    // ============================================================
    //  RENDER - ГЛАВНАЯ ФУНКЦИЯ РЕНДЕРИНГА
    // ============================================================

    render() {
        console.log('🎨 Rendering...');

        this.renderExplorer();
        this.renderTabs();
        this.renderPalette();
        this.renderCanvas();
        this.renderProperties();
        this.renderTerminal();

        this.logTerminal(`📊 Rendered: ${this.elements.length} elements, ${this.pages.length} pages`, 'info');
    }

    // ============================================================
    //  RENDER EXPLORER - ДРЕВОВИДНАЯ СТРУКТУРА
    // ============================================================

    renderExplorer() {
        const container = this.els.explorerList;
        container.innerHTML = '';

        if (this.pages.length === 0) {
            container.innerHTML = '<div style="color:#555;padding:20px;text-align:center;">No pages</div>';
            return;
        }

        this.pages.forEach(page => {
            const pageElements = this.elements.filter(el => el.page === page);

            const pageItem = document.createElement('div');
            pageItem.className = `explorer-item${this.selectedPage === page ? ' active' : ''}`;
            pageItem.innerHTML = `
                <span class="icon">📄</span>
                ${page}
                <span class="badge">${pageElements.length}</span>
            `;
            pageItem.addEventListener('click', () => {
                this.selectedPage = page;
                this.renderExplorer();
                this.renderTabs();
                this.renderCanvas();
                this.renderTerminal();
                this.logTerminal(`📄 Switched to page: ${page}`, 'info');
                this.saveState();
            });
            container.appendChild(pageItem);

            pageElements.forEach(el => {
                const elItem = document.createElement('div');
                elItem.className = `explorer-item sub${this.selectedElement?.id === el.id ? ' active' : ''}`;
                elItem.innerHTML = `
                    <span class="type-icon">${this.getTypeIcon(el.type)}</span>
                    ${el.type}: ${el.content?.substring(0, 20) || '...'}
                    <span class="badge">${el.id.substring(0, 6)}</span>
                `;
                elItem.addEventListener('click', () => {
                    this.selectElement(el.id);
                });
                container.appendChild(elItem);
            });
        });
    }

    renderTabs() {
        const container = this.els.editorTabs;
        container.innerHTML = '';

        if (this.pages.length === 0) {
            container.innerHTML = '<div style="color:#555;padding:4px 16px;font-size:12px;">No pages</div>';
            return;
        }

        this.pages.forEach((page) => {
            const tab = document.createElement('div');
            tab.className = `editor-tab${page === this.selectedPage ? ' active' : ''}`;
            tab.innerHTML = `${page} <span class="close" data-page="${page}">✕</span>`;
            tab.addEventListener('click', (e) => {
                if (e.target.classList.contains('close')) {
                    this.deletePage(page);
                    return;
                }
                this.selectedPage = page;
                this.renderTabs();
                this.renderExplorer();
                this.renderCanvas();
                this.renderTerminal();
                this.logTerminal(`📄 Switched to page: ${page}`, 'info');
                this.saveState();
            });
            container.appendChild(tab);
        });
    }

    renderPalette() {
        const container = this.els.paletteItems;
        container.innerHTML = '';

        const types = [...new Set(this.elements.map(el => el.type))];

        if (types.length === 0) {
            container.innerHTML = '<div style="color:#555;padding:20px;text-align:center;grid-column:1/-1;">No elements</div>';
            return;
        }

        types.forEach(type => {
            const item = document.createElement('div');
            item.className = 'palette-item';
            item.draggable = true;
            item.innerHTML = `
                <span class="icon">${this.getTypeIcon(type)}</span>
                <span class="label">${type}</span>
                <span class="tag">&lt;${type.toLowerCase()}&gt;</span>
            `;
            container.appendChild(item);
        });
    }

    renderCanvas() {
        this.canvas.clear();
        this.canvasObjects = {};

        const pageElements = this.elements.filter(el => el.page === this.selectedPage);

        pageElements.forEach(el => {
            const obj = this.createFabricObject(el);
            if (obj) {
                obj.elementId = el.id;
                obj.elementData = el;
                this.canvas.add(obj);
                this.canvasObjects[el.id] = obj;
            }
        });

        this.canvas.renderAll();
    }

    renderProperties() {
        const container = this.els.propertyRows;
        if (this.selectedElement) {
            this.renderPropertiesForElement(this.selectedElement);
        } else {
            container.innerHTML = '<div style="color:#555;text-align:center;padding:20px;">Select an element</div>';
        }
    }

    renderPropertiesForElement(element) {
        const container = this.els.propertyRows;
        container.innerHTML = '';

        const props = [
            { label: 'Type', value: element.type },
            { label: 'Content', value: element.content, editable: true, key: 'content' },
            { label: 'Color', value: element.data.color || '#333', type: 'color', key: 'color' },
            { label: 'Size', value: element.data.font_size?.replace('px', '') || '16', unit: 'px', editable: true, key: 'font_size' },
            { label: 'X', value: String(element.x || 100), unit: 'px', editable: true, key: 'x' },
            { label: 'Y', value: String(element.y || 100), unit: 'px', editable: true, key: 'y' },
        ];

        props.forEach(prop => {
            const row = document.createElement('div');
            row.className = 'prop-row';
            row.dataset.propKey = prop.key || prop.label.toLowerCase();

            let valueHTML = '';
            if (prop.type === 'color') {
                valueHTML = `
                    <span class="prop-value color-picker">
                        <input type="color" value="${prop.value}" data-key="${prop.key || prop.label.toLowerCase()}">
                    </span>
                `;
            } else if (prop.editable) {
                valueHTML = `<span class="prop-value" contenteditable="true" data-key="${prop.key || prop.label.toLowerCase()}">${prop.value}</span>`;
            } else {
                valueHTML = `<span class="prop-value">${prop.value}</span>`;
            }

            row.innerHTML = `
                <span class="prop-label">${prop.label}</span>
                ${valueHTML}
                ${prop.unit ? `<span class="unit">${prop.unit}</span>` : ''}
            `;
            container.appendChild(row);
        });
    }

    renderTerminal() {
        const container = this.els.terminalOutput;
        const name = this.projectData?.projectName || 'None';
        const pageName = this.selectedPage || 'None';
        container.innerHTML = `
            <div class="log-line"><span class="prompt">➜</span> <span class="info">Editor loaded</span></div>
            <div class="log-line"><span class="prompt">➜</span> Project: <span class="success">${name}</span></div>
            <div class="log-line"><span class="prompt">➜</span> Page: <span class="info">${pageName}</span></div>
            <div class="log-line"><span class="prompt">➜</span> Elements: <span class="info">${this.elements.filter(el => el.page === this.selectedPage).length}</span></div>
            <div class="log-line"><span class="prompt">➜</span> Status: <span class="success">Ready</span></div>
        `;
    }

    renderEmptyState() {
        this.els.explorerList.innerHTML = '<div style="color:#555;padding:20px;text-align:center;">No project loaded</div>';
        this.els.editorTabs.innerHTML = '<div style="color:#555;padding:4px 16px;font-size:12px;">No project</div>';
        this.els.paletteItems.innerHTML = '<div style="color:#555;padding:20px;text-align:center;grid-column:1/-1;">Load a project</div>';
        this.els.terminalOutput.innerHTML = `
            <div class="log-line"><span class="prompt">➜</span> <span class="info">No project loaded</span></div>
            <div class="log-line"><span class="prompt">➜</span> Open a project from <span class="info">/load</span></div>
        `;
    }

    // ============================================================
    //  FABRIC OBJECTS
    // ============================================================

    createFabricObject(el) {
        let obj = null;
        const style = el.data;
        const x = el.x || 100;
        const y = el.y || 100;
        const fontSize = parseInt(style.font_size) || 16;
        const color = style.color || '#333';

        switch (el.type) {
            case 'Text':
            case 'Heading':
                obj = new fabric.IText(el.content || 'Text', {
                    left: x,
                    top: y,
                    fontSize: fontSize,
                    fill: color,
                    fontFamily: style.font_family || 'Arial',
                    fontWeight: style.font_weight || 'normal',
                });
                break;

            case 'Button':
                obj = new fabric.Group([
                    new fabric.Rect({
                        width: 120,
                        height: 40,
                        rx: 4,
                        fill: style.background_color || '#007acc',
                    }),
                    new fabric.IText(el.content || 'Button', {
                        left: 60,
                        top: 20,
                        fontSize: 14,
                        fill: style.color || '#fff',
                        originX: 'center',
                        originY: 'center',
                    })
                ], {
                    left: x,
                    top: y,
                });
                break;

            case 'Container':
                obj = new fabric.Rect({
                    left: x,
                    top: y,
                    width: parseInt(style.width) || 200,
                    height: parseInt(style.height) || 100,
                    fill: style.background_color || '#f5f5f5',
                    stroke: style.border || '#ddd',
                    strokeWidth: 1,
                    rx: parseInt(style.border_radius) || 4,
                });
                break;

            default:
                obj = new fabric.IText(el.content || 'Element', {
                    left: x,
                    top: y,
                    fontSize: 16,
                    fill: color,
                });
        }

        return obj;
    }

    getTypeIcon(type) {
        const icons = {
            'Text': '📝',
            'Heading': '📰',
            'Button': '🔘',
            'Container': '📦',
            'Image': '🖼️',
            'Link': '🔗',
            'Input': '📋',
            'Textarea': '📄',
            'List': '📑'
        };
        return icons[type] || '📄';
    }

    // ============================================================
    //  UPDATE - ИГРОВОЙ ЦИКЛ
    // ============================================================

    startUpdateLoop() {
        console.log('🔄 Starting update loop (60 FPS)...');
        this.update();
        this.updateInterval = setInterval(() => {
            this.update();
        }, 1000 / 60);
    }

    update() {
        this.frameCount++;
        if (this.isLoading) return;

        if (this.frameCount % 60 === 0) {
            this.updateUI();
        }
    }

    updateUI() {
        if (this.selectedElement) {
            const obj = this.canvasObjects[this.selectedElement.id];
            if (obj) {
                this.selectedElement.x = Math.round(obj.left || 0);
                this.selectedElement.y = Math.round(obj.top || 0);
                if (obj.type === 'i-text') {
                    this.selectedElement.content = obj.text || '';
                }
            }
        }
    }

    // ============================================================
    //  СОБЫТИЯ
    // ============================================================

    setupEvents() {
        this.canvas.on('selection:created', (e) => {
            this.onElementSelected(e.selected[0]);
        });
        this.canvas.on('selection:updated', (e) => {
            this.onElementSelected(e.selected[0]);
        });
        this.canvas.on('selection:cleared', () => {
            this.onElementDeselected();
        });

        this.canvas.on('object:modified', (e) => {
            this.onElementModified(e.target);
        });
        this.canvas.on('object:moving', (e) => {
            this.dirty = true;
            this.triggerAutoSave();
        });
        this.canvas.on('object:scaling', (e) => {
            this.dirty = true;
            this.triggerAutoSave();
        });

        document.querySelectorAll('.terminal-tab').forEach(tab => {
            tab.addEventListener('click', function () {
                document.querySelectorAll('.terminal-tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
            });
        });

        document.getElementById('refreshExplorerBtn').addEventListener('click', () => {
            this.renderExplorer();
            this.showToast('🔄', 'Explorer refreshed', 'success');
        });
        document.getElementById('refreshPaletteBtn').addEventListener('click', () => {
            this.renderPalette();
            this.showToast('🔄', 'Palette refreshed', 'success');
        });

        document.getElementById('newPageBtn').addEventListener('click', () => {
            const name = prompt('Enter page name:', 'New Page');
            if (name && name.trim()) {
                this.addPage(name.trim());
            }
        });

        document.addEventListener('input', (e) => {
            const target = e.target;
            if (target.classList.contains('prop-value') && target.contentEditable === 'true') {
                const key = target.dataset.key;
                if (key && this.selectedElement) {
                    this.updateElementProperty(key, target.textContent);
                    this.dirty = true;
                    this.triggerAutoSave();
                }
            }
        });

        document.addEventListener('change', (e) => {
            const target = e.target;
            if (target.type === 'color') {
                const key = target.dataset.key;
                if (key && this.selectedElement) {
                    this.updateElementProperty(key, target.value);
                    this.dirty = true;
                    this.triggerAutoSave();
                }
            }
        });

        this.setupSearch();
    }

    // ============================================================
    //  ВЫБОР ЭЛЕМЕНТА
    // ============================================================

    selectElement(id) {
        const element = this.elements.find(el => el.id === id);
        if (element) {
            this.selectedElement = element;
            this.renderExplorer();
            this.renderProperties();
            this.logTerminal(`📌 Selected: ${element.type} (${element.id})`, 'info');
            this.saveState();

            const obj = this.canvasObjects[id];
            if (obj) {
                this.canvas.setActiveObject(obj);
                this.canvas.renderAll();
            }
        }
    }

    onElementSelected(obj) {
        const elementId = obj.elementId;
        const element = this.elements.find(el => el.id === elementId);
        if (element) {
            this.selectedElement = element;
            this.renderExplorer();
            this.renderProperties();
            this.logTerminal(`📌 Selected: ${element.type} (${element.id})`, 'info');
            this.saveState();
        }
    }

    onElementDeselected() {
        this.selectedElement = null;
        this.renderProperties();
    }

    // ============================================================
    //  ИЗМЕНЕНИЕ ЭЛЕМЕНТА
    // ============================================================

    onElementModified(obj) {
        const elementId = obj.elementId;
        const element = this.elements.find(el => el.id === elementId);
        if (element) {
            element.x = Math.round(obj.left || 0);
            element.y = Math.round(obj.top || 0);
            if (obj.type === 'i-text') {
                element.content = obj.text || '';
                element.data.content = obj.text || '';
            }
            this.dirty = true;
            this.triggerAutoSave();
            this.logTerminal(`✏️ Modified: ${element.type}`, 'info');
        }
    }

    updateElementProperty(key, value) {
        if (!this.selectedElement) return;

        const element = this.selectedElement;
        const obj = this.canvasObjects[element.id];

        switch (key) {
            case 'content':
                element.content = value;
                element.data.content = value;
                if (obj && obj.type === 'i-text') {
                    obj.setText(value);
                }
                break;
            case 'color':
                element.data.color = value;
                if (obj && obj.type === 'i-text') {
                    obj.setFill(value);
                }
                break;
            case 'font_size':
                element.data.font_size = value + 'px';
                if (obj && obj.type === 'i-text') {
                    obj.setFontSize(parseInt(value) || 16);
                }
                break;
            case 'x':
                element.x = parseInt(value) || 0;
                if (obj) obj.setLeft(parseInt(value) || 0);
                break;
            case 'y':
                element.y = parseInt(value) || 0;
                if (obj) obj.setTop(parseInt(value) || 0);
                break;
        }

        this.canvas.renderAll();
        this.dirty = true;
    }

    // ============================================================
    //  АВТОСОХРАНЕНИЕ
    // ============================================================

    triggerAutoSave() {
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        this.saveTimeout = setTimeout(() => {
            this.autoSave();
        }, 1000);
    }

    async autoSave() {
        if (!this.dirty || !this.projectId) return;

        try {
            for (const el of this.elements) {
                const obj = this.canvasObjects[el.id];
                if (obj) {
                    el.data.left = String(Math.round(obj.left || 0));
                    el.data.top = String(Math.round(obj.top || 0));
                    if (obj.type === 'i-text') {
                        el.data.content = obj.text || '';
                    }
                }
            }

            for (const el of this.elements) {
                const page = el.page;
                if (this.projectData.project.pages[page]) {
                    this.projectData.project.pages[page].elements[el.id] = el.data;
                }
            }

            const response = await fetch(`/api/project/${this.projectId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.projectData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            this.dirty = false;
            this.lastSave = new Date();
            this.logTerminal('💾 Auto-saved', 'success');
            this.saveState();

        } catch (error) {
            console.error('❌ Auto-save failed:', error);
            this.logTerminal(`❌ Auto-save failed: ${error.message}`, 'error');
        }
    }

    // ============================================================
    //  СОХРАНЕНИЕ СОСТОЯНИЯ (localStorage)
    // ============================================================

    saveState() {
        try {
            const state = {
                projectId: this.projectId,
                selectedPage: this.selectedPage,
                selectedElement: this.selectedElement?.id || null,
                timestamp: Date.now()
            };
            localStorage.setItem('editor_state', JSON.stringify(state));
        } catch (e) {
            console.warn('Failed to save state:', e);
        }
    }

    restoreState() {
        try {
            const saved = localStorage.getItem('editor_state');
            if (saved) {
                const state = JSON.parse(saved);
                console.log('📦 Restored state:', state);
                if (state.projectId === this.projectId) {
                    if (state.selectedPage) {
                        this.selectedPage = state.selectedPage;
                    }
                    this._restoreElementId = state.selectedElement;
                }
            }
        } catch (e) {
            console.warn('Failed to restore state:', e);
        }
    }

    restoreSelectedElement() {
        if (this._restoreElementId) {
            const el = this.elements.find(e => e.id === this._restoreElementId);
            if (el) {
                this.selectElement(el.id);
                this._restoreElementId = null;
            }
        }
    }

    // ============================================================
    //  ПЕРЕД ВЫХОДОМ
    // ============================================================

    setupBeforeUnload() {
        window.addEventListener('beforeunload', () => {
            if (this.dirty) {
                this.autoSave();
            }
            this.saveState();
        });
    }

    // ============================================================
    //  УПРАВЛЕНИЕ СТРАНИЦАМИ
    // ============================================================

    addPage(name) {
        if (!this.projectData) return;
        if (this.pages.includes(name)) {
            this.showToast('⚠️', `Page "${name}" already exists`, 'warning');
            return;
        }

        this.pages.push(name);
        this.projectData.project.pages[name] = { title: name, elements: {} };
        this.selectedPage = name;
        this.dirty = true;

        this.render();
        this.triggerAutoSave();
        this.logTerminal(`📄 Added page: ${name}`, 'success');
        this.showToast('📄', `Page "${name}" created`, 'success');
        this.saveState();
    }

    deletePage(name) {
        if (this.pages.length <= 1) {
            this.showToast('⚠️', 'Cannot delete the last page', 'warning');
            return;
        }

        if (!confirm(`Delete page "${name}" and all its elements?`)) return;

        this.elements = this.elements.filter(el => el.page !== name);
        this.pages = this.pages.filter(p => p !== name);
        delete this.projectData.project.pages[name];

        if (this.selectedPage === name) {
            this.selectedPage = this.pages[0];
        }

        this.dirty = true;
        this.render();
        this.triggerAutoSave();
        this.logTerminal(`🗑️ Deleted page: ${name}`, 'warning');
        this.showToast('🗑️', `Page "${name}" deleted`, 'warning');
        this.saveState();
    }

    // ============================================================
    //  SEARCH
    // ============================================================

    setupSearch() {
        const explorerSearch = document.getElementById('explorerSearchInput');
        const explorerClear = document.getElementById('explorerSearchClear');

        explorerSearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const items = document.querySelectorAll('#explorerList .explorer-item');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.classList.toggle('hidden', query !== '' && !text.includes(query));
            });
            explorerClear.classList.toggle('visible', query !== '');
        });

        explorerClear.addEventListener('click', () => {
            explorerSearch.value = '';
            explorerSearch.dispatchEvent(new Event('input'));
            explorerSearch.focus();
        });

        const paletteSearch = document.getElementById('paletteSearchInput');
        const paletteClear = document.getElementById('paletteSearchClear');

        paletteSearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const items = document.querySelectorAll('#paletteItems .palette-item');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.classList.toggle('hidden', query !== '' && !text.includes(query));
            });
            paletteClear.classList.toggle('visible', query !== '');
        });

        paletteClear.addEventListener('click', () => {
            paletteSearch.value = '';
            paletteSearch.dispatchEvent(new Event('input'));
            paletteSearch.focus();
        });

        const propertiesSearch = document.getElementById('propertiesSearchInput');
        const propertiesClear = document.getElementById('propertiesSearchClear');

        propertiesSearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const rows = document.querySelectorAll('#propertyRows .prop-row');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.classList.toggle('hidden', query !== '' && !text.includes(query));
            });
            propertiesClear.classList.toggle('visible', query !== '');
        });

        propertiesClear.addEventListener('click', () => {
            propertiesSearch.value = '';
            propertiesSearch.dispatchEvent(new Event('input'));
            propertiesSearch.focus();
        });
    }

    // ============================================================
    //  TOAST
    // ============================================================

    showToast(title, message, type = 'success') {
        const toast = document.getElementById('toast');
        const toastTitle = document.getElementById('toastTitle');
        const toastMessage = document.getElementById('toastMessage');

        toast.className = 'toast ' + type;
        toastTitle.textContent = title;
        toastMessage.textContent = message;

        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 4000);
    }

    logTerminal(message, type = 'info') {
        const container = this.els.terminalOutput;
        const colors = {
            info: 'var(--accent-blue)',
            success: '#27c93f',
            error: '#e81123',
            warning: '#ffbd2e'
        };

        const line = document.createElement('div');
        line.className = 'log-line';
        line.innerHTML = `
            <span style="color:${colors[type] || '#969696'};">${message}</span>
        `;
        container.appendChild(line);
        container.scrollTop = container.scrollHeight;
    }
}

// ============================================================
//  ИНИЦИАЛИЗАЦИЯ
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    const editor = new Editor();
    window.editor = editor;

    console.log('🎨 Flux Studio - Editor');
    console.log('🌳 Explorer with tree structure');
    console.log('💾 Auto-save on every change');
    console.log('💡 Press Ctrl+P for global search');
});