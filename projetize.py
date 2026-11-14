    function renderDeviceIcon(d) {
        if (d.iconFile) return `<img src="/uploads/icons/${d.iconFile}" style="width:24px;height:24px;object-fit:contain;">`;
        return d.icon || '📦';
    }
    function renderConnIcon(c) {
        if (c.iconFile) return `<img src="/uploads/icons/${c.iconFile}" style="width:24px;height:24px;object-fit:contain;">`;
        return c.icon || '🔌';
    }
    
    function renderPalette() {
        const cont = document.getElementById('categories-container');
        if (!cont) return;
        cont.innerHTML = '';
        for (const [cn, cd] of Object.entries(categories)) {
            const div = document.createElement('div');
            div.className = 'category';
            const icon = cd.iconFile ? `<img src="/uploads/icons/${cd.iconFile}" style="width:16px;height:16px;">` : (cd.icon || '📁');
            const isAdmin = userRole === 'admin' || userRole === 'master';
            div.innerHTML = `<div class="category-header"><h3>${icon} ${cn}</h3>${isAdmin ? `<div class="category-actions"><button onclick="editCategory('${cn.replace(/'/g,"\\'")}')">✏️</button><button onclick="deleteCategory('${cn.replace(/'/g,"\\'")}')">🗑</button><button onclick="addDeviceToCategory('${cn.replace(/'/g,"\\'")}')">➕</button></div>` : ''}</div><div id="cat-${cn.replace(/[^a-z0-9]/gi,'_')}"></div>`;
            cont.appendChild(div);
            const cc = document.getElementById(`cat-${cn.replace(/[^a-z0-9]/gi,'_')}`);
            if (cd.devices) {
                cd.devices.forEach((d, i) => {
                    const el = document.createElement('div');
                    el.className = 'component';
                    el.draggable = true;
                    el.innerHTML = `<div class="component-icon">${renderDeviceIcon(d)}</div><div class="component-info"><div class="component-name">${d.name}</div><div class="component-desc">${d.desc || ''}</div></div>${isAdmin ? `<div class="component-actions"><button onclick="editDevice('${cn.replace(/'/g,"\\'")}',${i})">✏️</button><button onclick="deleteDevice('${cn.replace(/'/g,"\\'")}',${i})">🗑</button></div>` : ''}`;
                    el.addEventListener('dragstart', e => {
                        e.dataTransfer.setData('text/plain', JSON.stringify({name: d.name, icon: d.icon, type: d.type, subtype: d.subtype || '', color: d.color, iconFile: d.iconFile || null}));
                    });
                    cc.appendChild(el);
                });
            }
        }
        if (customDevices.length > 0) {
            const isAdmin = userRole === 'admin' || userRole === 'master';
            const cd = document.createElement('div');
            cd.className = 'category';
            cd.innerHTML = `<div class="category-header"><h3>🎨 Personalizados</h3>${isAdmin ? '<div class="category-actions"><button onclick="openAddDeviceModal()">➕</button></div>' : ''}</div><div id="custom-dev-cont"></div>`;
            cont.appendChild(cd);
            const cdc = document.getElementById('custom-dev-cont');
            customDevices.forEach((d, i) => {
                const el = document.createElement('div');
                el.className = 'component';
                el.draggable = true;
                el.innerHTML = `<div class="component-icon">${renderDeviceIcon(d)}</div><div class="component-info"><div class="component-name">${d.name}</div><div class="component-desc">${d.desc || 'Custom'}</div></div>`;
                el.addEventListener('dragstart', e => {
                    e.dataTransfer.setData('text/plain', JSON.stringify({name: d.name, icon: d.icon, type: d.type || 'custom', subtype: 'custom', color: d.color || '#005f99', iconFile: d.iconFile || null}));
                });
                cdc.appendChild(el);
            });
        }
    }
    
    function renderConnectionsPalette() {
        const cont = document.getElementById('connections-container');
        if (!cont) return;
        cont.innerHTML = '';
        for (const [cn, cd] of Object.entries(connectionCategories)) {
            if (!cd.connections || cd.connections.length === 0) continue;
            const div = document.createElement('div');
            div.className = 'category';
            div.innerHTML = `<div class="category-header"><h3>${cd.icon || '🔌'} ${cn}</h3></div><div id="conn-${cn.replace(/[^a-z0-9]/gi,'_')}"></div>`;
            cont.appendChild(div);
            const cc = document.getElementById(`conn-${cn.replace(/[^a-z0-9]/gi,'_')}`);
            cd.connections.forEach(c => {
                const el = document.createElement('div');
                el.className = 'component';
                el.innerHTML = `<div class="component-icon">${renderConnIcon(c)}</div><div class="component-info"><div class="component-name">${c.name}</div><div class="component-desc">${c.desc || c.speed || ''}</div></div>`;
                cc.appendChild(el);
            });
        }
    }
    
    function applyZoomToCanvas() {
        canvas.style.transform = `scale(${zoom})`;
        canvas.style.transformOrigin = '0 0';
    }
    function zoomIn() { zoom = Math.min(zoom + 0.1, 3); applyZoomToCanvas(); saveUserData(); }
    function zoomOut() { zoom = Math.max(zoom - 0.1, 0.3); applyZoomToCanvas(); saveUserData(); }
    function resetZoom() { zoom = 1; applyZoomToCanvas(); saveUserData(); }
    function iconZoomIn() { iconSize = Math.min(iconSize + 4, 80); saveUserData(); }
    function iconZoomOut() { iconSize = Math.max(iconSize - 4, 20); saveUserData(); }
    function resetIconSize() { iconSize = 36; saveUserData(); }
    
    function drawGrid() {
        if (!showGrid) return;
        ctx.save();
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 0.5;
        for (let x = 0; x < canvas.width; x += 50) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke(); }
        for (let y = 0; y < canvas.height; y += 50) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke(); }
        ctx.restore();
    }
    function drawBg() {
        if (bgImgObj && bgImgObj.complete && bgImgObj.src && bgW > 0 && bgH > 0) {
            ctx.save();
            ctx.globalAlpha = bgOpacity;
            ctx.drawImage(bgImgObj, bgX, bgY, bgW, bgH);
            ctx.globalAlpha = 1;
            if (bgSelected) {
                ctx.strokeStyle = '#005f99';
                ctx.lineWidth = 3;
                ctx.setLineDash([8, 6]);
                ctx.strokeRect(bgX, bgY, bgW, bgH);
                ctx.setLineDash([]);
            }
            ctx.restore();
        }
    }
    function drawFOV(cam) {
        if (!cam.angle) cam.angle = 0;
        if (!cam.fov) cam.fov = 80;
        const ar = cam.angle * Math.PI / 180;
        const fr = cam.fov * Math.PI / 180;
        const d = 100;
        const la = ar - fr/2, ra = ar + fr/2;
        const x1 = cam.x + Math.cos(la) * d, y1 = cam.y + Math.sin(la) * d;
        const x2 = cam.x + Math.cos(ra) * d, y2 = cam.y + Math.sin(ra) * d;
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(cam.x, cam.y);
        ctx.lineTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.fillStyle = 'rgba(0,95,153,0.2)';
        ctx.fill();
        ctx.strokeStyle = '#005f99';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.restore();
    }
    function drawSensorAnim(x, y, t) {
        for (let i = 0; i < 3; i++) {
            const p = (t + i*0.5) % 1;
            const r = 25 + p*30;
            const o = 0.5 * (1-p);
            ctx.save();
            ctx.beginPath();
            ctx.arc(x, y, r, 0, 2*Math.PI);
            ctx.strokeStyle = `rgba(0,95,153,${o})`;
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.restore();
        }
    }
    function drawConns() {
        connections.forEach((c, idx) => {
            const from = components.find(x => x.id === c.from);
            const to = components.find(x => x.id === c.to);
            if (!from || !to) return;
            const info = cableColors[c.type] || cableColors['cat6'];
            if (!info) return;
            const sel = idx === selectedConnectionIndex;
            ctx.save();
            ctx.setLineDash(info.type === 'wireless' ? [10, 8] : []);
            ctx.beginPath();
            ctx.moveTo(from.x, from.y);
            ctx.lineTo(to.x, to.y);
            ctx.strokeStyle = info.color;
            ctx.lineWidth = sel ? 4 : 2;
            ctx.stroke();
            ctx.restore();
        });
    }
    function drawShapes() {
        shapes.forEach(s => {
            ctx.save();
            ctx.strokeStyle = s.strokeColor || '#005f99';
            ctx.fillStyle = s.fillColor || 'rgba(0,0,0,0.05)';
            ctx.lineWidth = s.lineWidth || 2;
            switch (s.type) {
                case 'line':
                    ctx.beginPath();
                    ctx.moveTo(s.x1, s.y1);
                    ctx.lineTo(s.x2, s.y2);
                    ctx.stroke();
                    break;
                case 'door':
                    ctx.fillRect(s.x, s.y, 30, 50);
                    ctx.strokeRect(s.x, s.y, 30, 50);
                    break;
                case 'window':
                    ctx.fillRect(s.x, s.y, 60, 40);
                    ctx.strokeRect(s.x, s.y, 60, 40);
                    break;
                case 'text':
                    ctx.font = `${s.fontSize || 14}px Arial`;
                    ctx.fillStyle = s.textColor || '#212529';
                    ctx.fillText(s.text || 'Texto', s.x, s.y);
                    break;
            }
            ctx.restore();
        });
    }
    function drawComps() {
        components.forEach(c => {
            const sel = selectedComponents.includes(c);
            if (c.type === 'sensor') drawSensorAnim(c.x, c.y, sensorAnim);
            ctx.save();
            const h = iconSize/2;
            if (c.iconFile) {
                ctx.drawImage(getCachedImage(`/uploads/icons/${c.iconFile}`), c.x - h, c.y - h, iconSize, iconSize);
            } else {
                ctx.fillStyle = c.color || '#005f99';
                ctx.beginPath();
                ctx.arc(c.x, c.y, h, 0, 2*Math.PI);
                ctx.fill();
                ctx.fillStyle = '#fff';
                ctx.font = `${iconSize/2}px Arial`;
                ctx.fillText(c.icon || '📦', c.x - 12, c.y + 8);
            }
            ctx.fillStyle = '#005f99';
            ctx.font = '12px Arial';
            ctx.fillText(c.name, c.x - 30, c.y - h - 5);
            if (c.ip) {
                ctx.fillStyle = '#6c757d';
                ctx.font = '10px Arial';
                ctx.fillText(c.ip, c.x - 25, c.y - h - 15);
            }
            if (sel) {
                ctx.strokeStyle = '#005f99';
                ctx.lineWidth = 2;
                ctx.strokeRect(c.x - h - 4, c.y - h - 4, iconSize + 8, iconSize + 8);
            }
            if (c.type === 'camera') drawFOV(c);
            ctx.restore();
        });
        sensorAnim = (sensorAnim + 0.01) % 1;
    }
    function drawAll() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawBg();
        if (showGrid) drawGrid();
        drawShapes();
        drawConns();
        drawComps();
        trafficAnim = (trafficAnim + 0.015) % 1;
        requestAnimationFrame(drawAll);
    }
    drawAll();
    
    function getMousePos(e) {
        const r = canvas.getBoundingClientRect();
        const sx = canvas.width / r.width;
        const sy = canvas.height / r.height;
        let cx = e.clientX, cy = e.clientY;
        if (e.touches) { cx = e.touches[0].clientX; cy = e.touches[0].clientY; }
        return {x: (cx - r.left) * sx, y: (cy - r.top) * sy};
    }
    
    function handleDown(e) {
        e.preventDefault();
        const {x, y} = getMousePos(e);
        lastMousePos = {x, y};
        if (shapeMode) { shapeStart = {x, y}; return; }
        for (let i = components.length - 1; i >= 0; i--) {
            const c = components[i];
            if (Math.hypot(x - c.x, y - c.y) < iconSize/2) {
                selectedComponents = [c];
                dragging = true;
                dragOffset = {x: c.x - x, y: c.y - y};
                showProperties(c);
                openProperties();
                return;
            }
        }
        for (const s of shapes) {
            if (s.type === 'text' && x >= s.x - 5 && x <= s.x + (s.text?.length * 7 || 50) && y >= s.y - 12 && y <= s.y + 6) {
                selectedShapes = [s];
                showShapeProperties(s);
                openProperties();
                return;
            }
        }
        selectedComponents = [];
        selectedShapes = [];
        selectedConnectionIndex = null;
        showProperties(null);
        closeProperties();
    }
    function handleMove(e) {
        const {x, y} = getMousePos(e);
        lastMousePos = {x, y};
        if (dragging && selectedComponents.length > 0) {
            const c = selectedComponents[0];
            c.x = x + dragOffset.x;
            c.y = y + dragOffset.y;
            saveUserData();
        }
    }
    function handleUp(e) {
        if (shapeMode && shapeStart) {
            const {x, y} = getMousePos(e);
            endShape(shapeStart, {x, y}, shapeMode);
            shapeStart = null;
            return;
        }
        dragging = false;
    }
    
    function endShape(start, end, type) {
        const s = {id: Date.now(), type, fillColor: '#f8f9fa', strokeColor: '#005f99', lineWidth: 2, rotation: 0};
        switch (type) {
            case 'line': s.x1 = start.x; s.y1 = start.y; s.x2 = end.x; s.y2 = end.y; break;
            case 'door': s.x = end.x; s.y = end.y; break;
            case 'window': s.x = Math.min(start.x, end.x); s.y = Math.min(start.y, end.y); break;
            case 'text':
                const txt = prompt('Digite o texto:', 'Texto');
                if (txt) { s.text = txt; s.x = end.x; s.y = end.y; s.fontSize = 14; s.textColor = '#212529'; }
                else return;
                break;
        }
        shapes.push(s);
        saveUserData();
        showToast(`✅ ${type} adicionado!`);
    }
    
    function openProperties() { document.getElementById('propertiesPanel').classList.add('open'); }
    function closeProperties() { document.getElementById('propertiesPanel').classList.remove('open'); }
    function closePropertiesPanel() { closeProperties(); }
    function togglePalette() { document.getElementById('palette').classList.toggle('collapsed'); }
    function toggleMobilePalette() {}
    function closeMobilePalette() {}
    
    function showProperties(c) {
        const div = document.getElementById('props-content');
        if (!c) { div.innerHTML = '<p style="color:var(--text-secondary);">Clique em um componente</p>'; return; }
        div.innerHTML = `
            <div class="property-group"><label>Nome</label><input type="text" id="p-name" value="${(c.name || '').replace(/"/g, '&quot;')}"></div>
            <div class="property-group"><label>X</label><input type="number" id="p-x" value="${Math.round(c.x)}"></div>
            <div class="property-group"><label>Y</label><input type="number" id="p-y" value="${Math.round(c.y)}"></div>
            <div class="property-group"><label>IP</label><input type="text" id="p-ip" value="${c.ip || ''}" placeholder="192.168.1.100"></div>
            <div class="property-group"><label>Porta</label><input type="number" id="p-port" value="${c.port || 80}"></div>
            <div class="modal-buttons">
                <button class="btn btn-info" onclick="accessDev(${c.id})">🌐 Acessar</button>
                <button class="btn btn-danger" onclick="deleteComp(${c.id})">🗑 Remover</button>
            </div>
        `;
        document.getElementById('p-name')?.addEventListener('change', e => { c.name = e.target.value; saveUserData(); });
        document.getElementById('p-x')?.addEventListener('change', e => { c.x = parseInt(e.target.value); saveUserData(); });
        document.getElementById('p-y')?.addEventListener('change', e => { c.y = parseInt(e.target.value); saveUserData(); });
        document.getElementById('p-ip')?.addEventListener('change', e => { c.ip = e.target.value; saveUserData(); });
        document.getElementById('p-port')?.addEventListener('change', e => { c.port = parseInt(e.target.value); saveUserData(); });
    }
    function showShapeProperties(s) {
        const div = document.getElementById('props-content');
        div.innerHTML = `<div class="property-group"><label>Tipo</label><input type="text" value="${s.type}" disabled></div><div class="modal-buttons"><button class="btn btn-danger" onclick="deleteShape(${s.id})">🗑 Excluir</button></div>`;
    }
    window.deleteShape = (id) => {
        shapes = shapes.filter(s => s.id !== id);
        saveUserData();
        closeProperties();
    };
    window.deleteSelectedShape = () => {
        if (selectedShapes.length > 0) {
            shapes = shapes.filter(s => s.id !== selectedShapes[0].id);
            selectedShapes = [];
            saveUserData();
            closeProperties();
        }
    };
    window.deleteComp = (id) => {
        if (confirm('Remover?')) {
            connections = connections.filter(c => c.from !== id && c.to !== id);
            components = components.filter(c => c.id !== id);
            selectedComponents = [];
            saveUserData();
            closeProperties();
        }
    };
    window.deleteSelectedItems = () => {
        if (selectedComponents.length > 0 && confirm('Excluir?')) {
            const ids = selectedComponents.map(c => c.id);
            connections = connections.filter(c => !ids.includes(c.from) && !ids.includes(c.to));
            components = components.filter(c => !ids.includes(c.id));
            selectedComponents = [];
            saveUserData();
            closeProperties();
        }
    };
    window.accessDev = (id) => {
        const c = components.find(x => x.id === id);
        if (c && c.ip) {
            let url = c.ip;
            if (!url.startsWith('http')) url = 'http://' + url;
            if (c.port && c.port !== 80) url += ':' + c.port;
            window.open(url, '_blank');
        } else showToast('⚠️ Sem IP');
    };
    
    // Acesso a dispositivos no canvas via duplo clique
    canvas.addEventListener('dblclick', (e) => {
        const {x, y} = getMousePos(e);
        for (const c of components) {
            if (Math.hypot(x - c.x, y - c.y) < iconSize/2 && c.ip) {
                let url = c.ip;
                if (!url.startsWith('http')) url = 'http://' + url;
                if (c.port && c.port !== 80) url += ':' + c.port;
                window.open(url, '_blank');
                return;
            }
        }
    });
    
    canvas.addEventListener('dragover', e => e.preventDefault());
    canvas.addEventListener('drop', e => {
        e.preventDefault();
        const {x, y} = getMousePos(e);
        const data = JSON.parse(e.dataTransfer.getData('text/plain'));
        components.push({id: Date.now(), name: data.name, x, y, icon: data.icon, iconFile: data.iconFile, color: data.color, type: data.type, ip: '', port: 80});
        saveUserData();
        showToast(`✅ ${data.name} adicionado`);
    });
    
    canvas.addEventListener('touchstart', handleDown, {passive: false});
    canvas.addEventListener('touchmove', handleMove, {passive: false});
    canvas.addEventListener('touchend', handleUp);
    canvas.addEventListener('mousedown', handleDown);
    canvas.addEventListener('mousemove', handleMove);
    canvas.addEventListener('mouseup', handleUp);
    
    function newProject() {
        if (confirm('Novo projeto?')) {
            components = []; connections = []; shapes = [];
            bgImg = null; bgImgObj = null;
            saveUserData();
            closeProperties();
        }
    }
    function saveProjectToFile() {
        const p = {components, connections, shapes, background: bgImg, backgroundOpacity: bgOpacity, backgroundWidth: bgW, backgroundHeight: bgH, backgroundX: bgX, backgroundY: bgY};
        const blob = new Blob([JSON.stringify(p, null, 2)], {type: 'application/json'});
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `projeto_${Date.now()}.projetize`;
        a.click();
    }
    function loadProjectFromFile() {
        const inp = document.createElement('input');
        inp.type = 'file';
        inp.accept = '.projetize,.json';
        inp.onchange = e => {
            const f = e.target.files[0];
            if (!f) return;
            const r = new FileReader();
            r.onload = ev => {
                try {
                    const d = JSON.parse(ev.target.result);
                    components = d.components || [];
                    connections = d.connections || [];
                    shapes = d.shapes || [];
                    if (d.background) {
                        bgImg = d.background;
                        bgOpacity = d.backgroundOpacity || 0.8;
                        bgW = d.backgroundWidth || 0;
                        bgH = d.backgroundHeight || 0;
                        bgX = d.backgroundX || 0;
                        bgY = d.backgroundY || 0;
                        bgImgObj = new Image();
                        bgImgObj.src = bgImg;
                    }
                    saveUserData();
                    showToast('✅ Projeto carregado');
                } catch(err) { showToast('Erro: ' + err.message); }
            };
            r.readAsText(f);
        };
        inp.click();
    }
    function exportPDF() {
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        drawShapes();
        drawConns();
        drawComps();
        const img = canvas.toDataURL('image/png');
        const w = window.open('', '_blank');
        w.document.write(`<html><body style="margin:0;padding:20px;"><img src="${img}" style="max-width:100%;"><script>window.print();<\\/script></body></html>`);
        showToast('📄 PDF gerado');
    }
    function exportPDFWithList() { exportPDF(); }
    function generateBudget() {
        let t = '📋 LISTA DE EQUIPAMENTOS\n\nData: ' + new Date().toLocaleString() + '\n\n';
        const byType = {};
        components.forEach(c => {
            const ty = c.type || 'custom';
            if (!byType[ty]) byType[ty] = [];
            byType[ty].push(c);
        });
        for (const [ty, arr] of Object.entries(byType)) {
            t += `\n📌 ${ty.toUpperCase()}:\n`;
            arr.forEach(c => { t += `   ✅ ${c.name}`; if (c.ip) t += ` (IP: ${c.ip})`; t += '\n'; });
        }
        const blob = new Blob([t], {type: 'text/plain'});
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `orcamento_${Date.now()}.txt`;
        a.click();
        showToast('💰 Orçamento gerado');
    }
    function toggleGrid() { showGrid = !showGrid; }
    function setShapeMode(m) {
        shapeMode = m;
        document.querySelectorAll('.shape-btn').forEach(b => b.classList.remove('active'));
        if (event && event.target) event.target.classList.add('active');
    }
    function cancelShapeMode() {
        shapeMode = null;
        document.querySelectorAll('.shape-btn').forEach(b => b.classList.remove('active'));
    }
    function toggleShapesToolbar() {
        const t = document.getElementById('shapesToolbar');
        t.style.display = t.style.display === 'none' ? 'flex' : 'none';
    }
    
    // === LOGIN ===
    async function loadLoginBgConfig() {
        try {
            const r = await fetch('/api/login_bg_config');
            const d = await r.json();
            if (d.success) { loginBgConfig = d.config; applyLoginBg(); }
        } catch(e) {}
    }
    function applyLoginBg() {
        const img = document.getElementById('loginBgMedia');
        const vid = document.getElementById('loginBgVideo');
        const mtx = document.getElementById('matrixBg');
        img.style.display = 'none';
        vid.style.display = 'none';
        img.src = '';
        vid.src = '';
        mtx.style.display = 'block';
        if (loginBgConfig.type === 'image' && loginBgConfig.filename) {
            img.src = `/uploads/login_bg/${loginBgConfig.filename}?t=${Date.now()}`;
            img.style.display = 'block';
            img.style.opacity = loginBgConfig.opacity || 0.35;
            mtx.style.display = 'none';
        } else if (loginBgConfig.type === 'video' && loginBgConfig.filename) {
            vid.src = `/uploads/login_bg/${loginBgConfig.filename}?t=${Date.now()}`;
            vid.style.display = 'block';
            vid.style.opacity = loginBgConfig.opacity || 0.35;
            vid.play().catch(() => {});
            mtx.style.display = 'none';
        } else {
            createMatrix('matrixBg');
        }
    }
    function createMatrix(id) {
        const c = document.getElementById(id);
        if (!c) return;
        c.innerHTML = '';
        const chars = '01アイウエオカキクケコサシスセソタチツテト';
        const cols = Math.floor(window.innerWidth / 20);
        for (let i = 0; i < cols; i++) {
            const col = document.createElement('div');
            col.className = 'matrix-column';
            col.style.left = (i * 20) + 'px';
            col.style.animationDuration = (Math.random() * 5 + 5) + 's';
            col.style.animationDelay = (Math.random() * 5) + 's';
            let txt = '';
            for (let j = 0; j < 40; j++) txt += chars[Math.floor(Math.random() * chars.length)] + '\n';
            col.textContent = txt;
            c.appendChild(col);
        }
    }
    function openLoginBgModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `<div class="modal-content" style="max-width:560px;"><h3>🎬 Fundo do Login</h3><div class="background-controls"><label><strong>📁 Escolher mídia</strong></label><input type="file" id="bgFile" accept="image/*,video/mp4,video/webm"><div class="image-preview" id="bgPrev"></div></div><div class="background-controls"><label><strong>Opacidade</strong></label><input type="range" id="bgOpac" min="0.05" max="1" step="0.05" value="${loginBgConfig.opacity || 0.35}"></div><div class="background-controls"><button class="btn btn-secondary" onclick="setLoginBgMatrix()" style="width:100%;">🔢 Restaurar Matrix</button></div><div class="modal-buttons"><button class="btn btn-primary" onclick="uploadLoginBg()">✅ Aplicar</button><button class="btn btn-danger" onclick="closeModal()">❌ Fechar</button></div></div>`;
        document.body.appendChild(modal);
        window.currentModal = modal;
        document.getElementById('bgFile').onchange = async e => {
            const f = e.target.files[0];
            if (!f) return;
            const url = URL.createObjectURL(f);
            const prev = document.getElementById('bgPrev');
            prev.innerHTML = f.type.startsWith('video/') ? `<video src="${url}" style="max-width:100%;max-height:150px;" autoplay loop muted></video>` : `<img src="${url}" style="max-width:100%;max-height:150px;">`;
            window.tempBgFile = f;
        };
    }
    window.setLoginBgMatrix = async () => {
        const r = await fetch('/api/login_bg_config', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'matrix'})});
        const d = await r.json();
        if (d.success) { loginBgConfig = d.config; applyLoginBg(); closeModal(); showToast('✅ Matrix restaurado'); }
    };
    window.uploadLoginBg = async () => {
        if (!window.tempBgFile) { showToast('⚠️ Selecione mídia'); return; }
        const f = window.tempBgFile;
        const base64 = await readImageAsBase64(f);
        const type = f.type.startsWith('video/') ? 'video' : 'image';
        const opac = parseFloat(document.getElementById('bgOpac').value) || 0.35;
        const r = await fetch('/api/upload_login_bg', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media: base64, type, opacity: opac})});
        const d = await r.json();
        if (d.success) { loginBgConfig = d.config; applyLoginBg(); closeModal(); showToast('✅ Fundo atualizado'); }
        window.tempBgFile = null;
    };
    
    async function doLogin() {
        const u = document.getElementById('loginUsername').value;
        const p = document.getElementById('loginPassword').value;
        const btn = document.getElementById('loginBtn');
        const err = document.getElementById('loginError');
        err.style.display = 'none';
        if (!u || !p) { err.textContent = 'Preencha usuário e senha'; err.style.display = 'block'; return; }
        btn.disabled = true;
        const orig = btn.innerHTML;
        btn.innerHTML = 'Entrando...';
        try {
            const r = await fetch('/api/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username: u, password: p})});
            const d = await r.json();
            if (d.success) {
                currentUser = u;
                userRole = d.role;
                if (d.role === 'admin' || d.role === 'master') document.getElementById('loginBgToggle').style.display = 'flex';
                document.getElementById('loginModal').style.display = 'none';
                document.getElementById('loadingOverlay').style.display = 'flex';
                document.getElementById('toolbar').style.display = 'flex';
                document.getElementById('userInfo').innerHTML = `<span>👤 ${u}</span><span class="user-role">${d.role.toUpperCase()}</span>`;
                if (d.role === 'admin' || d.role === 'master') {
                    ['adminUsersBtn','adminShapesBtn','adminCategoriesBtn','adminDevicesBtn','adminConnectionsBtn','resetDefaultsBtn','adminDevBtn','adminBgBtn'].forEach(id => {
                        const el = document.getElementById(id);
                        if (el) el.style.display = 'inline-block';
                    });
                }
                await Promise.all([loadDefaultConfig(), loadDefaultConnections()]);
                await loadUserData();
                document.getElementById('loadingOverlay').style.display = 'none';
                showToast(`Bem-vindo, ${u}!`);
            } else {
                err.textContent = d.error || 'Credenciais inválidas';
                err.style.display = 'block';
                btn.disabled = false;
                btn.innerHTML = orig;
            }
        } catch(e) {
            err.textContent = 'Erro de conexão';
            err.style.display = 'block';
            btn.disabled = false;
            btn.innerHTML = orig;
        }
    }
    function logout() { fetch('/api/logout', {method:'POST'}).then(() => location.reload()); }
    
    async function openUserManagement() {
        const r = await fetch('/api/users');
        const users = await r.json();
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `<div class="modal-content"><h3>👥 Usuários</h3><div id="userList"></div><div style="margin-top:15px;"><input type="text" id="newU" placeholder="Usuário"><input type="password" id="newP" placeholder="Senha"><select id="newR"><option value="viewer">Viewer</option><option value="admin">Admin</option></select><button class="btn btn-primary" onclick="addU()">➕ Adicionar</button></div><div class="modal-buttons"><button class="btn btn-danger" onclick="closeModal()">Fechar</button></div></div>`;
        document.body.appendChild(modal);
        window.currentModal = modal;
        const list = document.getElementById('userList');
        for (const [u, ud] of Object.entries(users)) {
            const d = document.createElement('div');
            d.className = 'user-item';
            d.style.cssText = 'background:var(--bg-tertiary);padding:10px;margin:5px 0;border-radius:5px;display:flex;justify-content:space-between;';
            d.innerHTML = `<div><strong>${u}</strong><br><small>${ud.role}</small></div>${ud.role !== 'master' ? `<button onclick="delU('${u}')" style="background:none;border:none;cursor:pointer;font-size:16px;">🗑</button>` : 'Master'}`;
            list.appendChild(d);
        }
    }
    window.addU = async () => {
        const u = document.getElementById('newU').value;
        const p = document.getElementById('newP').value;
        const r = document.getElementById('newR').value;
        const resp = await fetch('/api/users', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username: u, password: p, role: r})});
        const d = await resp.json();
        if (d.success) { closeModal(); openUserManagement(); }
        else showToast(d.error);
    };
    window.delU = async (u) => {
        if (!confirm(`Excluir ${u}?`)) return;
        const r = await fetch(`/api/users/${u}`, {method:'DELETE'});
        const d = await r.json();
        if (d.success) { closeModal(); openUserManagement(); }
    };
    
    // Admin modals básicos
    function openAddCategoryModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `<div class="modal-content"><h3>📁 Nova Categoria</h3><input type="text" id="catN" placeholder="Nome"><input type="text" id="catI" value="📁"><div class="modal-buttons"><button class="btn btn-primary" onclick="addCat()">OK</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
        document.body.appendChild(modal);
        window.currentModal = modal;
    }
    window.addCat = () => {
        const n = document.getElementById('catN').value;
        const i = document.getElementById('catI').value;
        if (!n || categories[n]) return;
        categories[n] = {icon: i || '📁', devices: []};
        saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette();
    };
    window.editCategory = () => {};
    window.deleteCategory = (c) => { if (confirm('Excluir?')) { delete categories[c]; saveUserData(); saveGlobalLibrary(); renderPalette(); } };
    window.addDeviceToCategory = (c) => {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `<div class="modal-content"><h3>➕ Novo em ${c}</h3><input type="text" id="dN" placeholder="Nome"><input type="text" id="dI" value="📦"><input type="text" id="dD" placeholder="Descrição"><input type="color" id="dC" value="#005f99"><input type="text" id="dT" placeholder="Tipo"><div class="modal-buttons"><button class="btn btn-primary" onclick="addDev('${c.replace(/'/g,"\\'")}')">OK</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
        document.body.appendChild(modal);
        window.currentModal = modal;
    };
    window.addDev = (c) => {
        const n = document.getElementById('dN').value;
        if (!n) return;
        categories[c].devices.push({name: n, icon: document.getElementById('dI').value || '📦', desc: document.getElementById('dD').value, color: document.getElementById('dC').value, type: document.getElementById('dT').value || 'custom', iconFile: null});
        saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette();
    };
    window.editDevice = () => {};
    window.deleteDevice = (c, i) => { if (confirm('Excluir?')) { categories[c].devices.splice(i, 1); saveUserData(); saveGlobalLibrary(); renderPalette(); } };
    window.openAddDeviceModal = () => {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `<div class="modal-content"><h3>🔧 Novo Equipamento</h3><input type="text" id="dN" placeholder="Nome"><input type="text" id="dI" value="📦"><input type="color" id="dC" value="#005f99"><input type="text" id="dT" placeholder="Tipo"><div class="modal-buttons"><button class="btn btn-primary" onclick="addCustomDev()">OK</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
        document.body.appendChild(modal);
        window.currentModal = modal;
    };
    window.addCustomDev = () => {
        const n = document.getElementById('dN').value;
        if (!n) return;
        customDevices.push({id: Date.now(), name: n, icon: document.getElementById('dI').value || '📦', color: document.getElementById('dC').value, type: document.getElementById('dT').value || 'custom', iconFile: null});
        saveUserData(); saveGlobalLibrary(); closeModal(); renderPalette();
    };
    window.openAddConnectionModal = () => {};
    window.addConnectionToCategory = () => {};
    window.addConnectionToCategoryConfirm = () => {};
    window.editCustomConnection = () => {};
    window.deleteCustomConnection = () => {};
    window.editCustomDevice = () => {};
    window.deleteCustomDevice = () => {};
    window.openCategoryIconModal = () => {};
    window.applyCategoryIcon = () => {};
    window.openConnectionIconModal = () => {};
    window.applyConnectionIcon = () => {};
    window.openDeviceIconModal = () => {};
    window.applyDeviceIcon = () => {};
    window.openCustomDeviceIconModal = () => {};
    window.applyCustomDeviceIcon = () => {};
    window.addConnectionFromModal = () => {};
    
    function openBackgroundModal() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `<div class="modal-content"><h3>🖼️ Planta</h3><div class="background-controls"><input type="file" id="bgUpload" accept="image/*"><div class="image-preview" id="bgPreview"></div><button class="btn btn-primary" onclick="importBg()">📤 Importar</button></div><div class="modal-buttons"><button class="btn btn-danger" onclick="closeModal()">Fechar</button></div></div>`;
        document.body.appendChild(modal);
        window.currentModal = modal;
    }
    window.importBg = async () => {
        const f = document.getElementById('bgUpload').files[0];
        if (!f) return;
        const b = await readImageAsBase64(f);
        const r = await fetch('/api/upload_background', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image: b, name: f.name})});
        const d = await r.json();
        if (d.success) {
            bgImg = d.url;
            bgImgObj = new Image();
            bgImgObj.onload = () => {
                bgW = bgImgObj.width;
                bgH = bgImgObj.height;
                bgX = 500;
                bgY = 500;
                saveUserData();
                closeModal();
            };
            bgImgObj.src = bgImg;
        }
    };
    window.openDevImageModal = () => {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `<div class="modal-content"><h3>🖼️ Foto Dev</h3><input type="file" id="devImg" accept="image/*"><div class="image-preview" id="devPrev"></div><div class="modal-buttons"><button class="btn btn-primary" onclick="uploadDevImg()">OK</button><button class="btn btn-danger" onclick="closeModal()">Cancelar</button></div></div>`;
        document.body.appendChild(modal);
        window.currentModal = modal;
        document.getElementById('devImg').onchange = async e => {
            const f = e.target.files[0];
            if (f) {
                const b = await readImageAsBase64(f);
                document.getElementById('devPrev').innerHTML = `<img src="${b}" style="max-width:100px;">`;
                window.tempDevImg = b;
            }
        };
    };
    window.uploadDevImg = async () => {
        if (!window.tempDevImg) return;
        const r = await fetch('/api/upload_dev_image', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image: window.tempDevImg})});
        const d = await r.json();
        if (d.success) setTimeout(() => location.reload(), 800);
        window.tempDevImg = null;
    };
    window.openDynamicBgModal = () => {};
    window.applyDynamicBg = () => {};
    
    window.closeIntroAndShowLogin = function() {
        document.getElementById('introScreen').style.display = 'none';
        document.getElementById('loginModal').style.display = 'flex';
        loadLoginBgConfig();
    };
    
    function loadDevImages() {
        const li = document.getElementById('loginDevImage');
        const bi = document.getElementById('badgeDevImage');
        const ia = document.getElementById('introDevAvatar');
        const img = new Image();
        img.onload = () => {
            if (li) { li.src = img.src; li.style.display = 'block'; document.getElementById('loginAvatarFallback').style.display = 'none'; }
            if (bi) bi.src = img.src;
            if (ia) ia.innerHTML = `<img src="${img.src}" style="width:100%;height:100%;object-fit:cover;">`;
        };
        if (devImageBase64 && devImageBase64.length > 20) {
            img.src = 'data:image/png;base64,' + devImageBase64;
        }
    }
    
    async function resetToDefaultConfig() {
        if (!confirm('Restaurar?')) return;
        await fetch('/api/reset_default_config', {method:'POST'});
        await loadDefaultConfig();
        categories = JSON.parse(JSON.stringify(defaultCategories));
        saveUserData(); saveGlobalLibrary(); renderPalette();
    }
    
    // ===== EXPORT WINDOW FUNCTIONS 2D =====
    window.newProject = newProject;
    window.saveProjectToFile = saveProjectToFile;
    window.loadProjectFromFile = loadProjectFromFile;
    window.exportPDF = exportPDF;
    window.exportPDFWithList = exportPDFWithList;
    window.generateBudget = generateBudget;
    window.zoomIn = zoomIn;
    window.zoomOut = zoomOut;
    window.resetZoom = resetZoom;
    window.iconZoomIn = iconZoomIn;
    window.iconZoomOut = iconZoomOut;
    window.resetIconSize = resetIconSize;
    window.togglePalette = togglePalette;
    window.closeModal = closeModal;
    window.openAddCategoryModal = openAddCategoryModal;
    window.doLogin = doLogin;
    window.logout = logout;
    window.openUserManagement = openUserManagement;
    window.setShapeMode = setShapeMode;
    window.cancelShapeMode = cancelShapeMode;
    window.toggleShapesToolbar = toggleShapesToolbar;
    window.toggleGrid = toggleGrid;
    window.resetToDefaultConfig = resetToDefaultConfig;
    window.closePropertiesPanel = closePropertiesPanel;
    window.toggleMobilePalette = toggleMobilePalette;
    window.closeMobilePalette = closeMobilePalette;
    window.openLoginBgModal = openLoginBgModal;
    window.loadLoginBgConfig = loadLoginBgConfig;
    window.applyLoginBg = applyLoginBg;
    window.renderPalette = renderPalette;
    window.renderConnectionsPalette = renderConnectionsPalette;
    window.openBackgroundModal = openBackgroundModal;
    window.openAddDeviceModal = openAddDeviceModal;
    window.openAddConnectionModal = openAddConnectionModal;
    window.openDevImageModal = openDevImageModal;
    window.openDynamicBgModal = openDynamicBgModal;
    
    // ===== INIT =====
    (async function init() {
        await loadDefaultConfig();
        await loadDefaultConnections();
        categories = JSON.parse(JSON.stringify(defaultCategories));
        renderPalette();
        renderConnectionsPalette();
    })();
    loadDevImages();
    createMatrix('matrixBg');
    closeProperties();
    loadLoginBgConfig();
    setTimeout(() => {
        const s = document.getElementById('splashScreen');
        if (s) s.style.display = 'none';
    }, 3000);
    
    // ==================== PARTE 3: SIMULADOR 3D ====================
    (function() {
        const DEVICE_CATALOG = {
            'router': {w:3.2, h:0.35, d:2.4, layout:'rack', label:'Router', builder:'router'},
            'switch_l2': {w:3.2, h:0.35, d:2.4, layout:'rack', label:'Switch L2', builder:'switch'},
            'switch_l3': {w:3.2, h:0.35, d:2.4, layout:'rack', label:'Switch L3', builder:'switch'},
            'switch_l2_poe': {w:3.2, h:0.35, d:2.4, layout:'rack', label:'Switch PoE', builder:'switch'},
            'switch_l3_poe': {w:3.2, h:0.35, d:2.4, layout:'rack', label:'Switch PoE', builder:'switch'},
            'olt': {w:3.2, h:0.7, d:2.4, layout:'rack', label:'OLT GPON', builder:'olt'},
            'patch': {w:3.2, h:0.25, d:0.3, layout:'rack', label:'Patch Panel', builder:'patch'},
            'nvr': {w:3.2, h:0.35, d:2.4, layout:'rack', label:'NVR', builder:'nvr'},
            'dvr': {w:3.2, h:0.35, d:2.4, layout:'rack', label:'DVR', builder:'nvr'},
            'pbx': {w:3.2, h:0.7, d:2.4, layout:'rack', label:'PABX', builder:'pbx'},
            'nobreak': {w:3.2, h:1.0, d:2.4, layout:'rack', label:'Nobreak', builder:'ups'},
            'server': {w:3.2, h:0.7, d:2.4, layout:'rack', label:'Servidor', builder:'server'},
            'nas': {w:3.2, h:1.0, d:2.4, layout:'rack', label:'NAS', builder:'nas'},
            'onu': {w:1.0, h:0.2, d:0.7, layout:'desktop', label:'ONU', builder:'onu'},
            'ont': {w:1.0, h:0.2, d:0.7, layout:'desktop', label:'ONT', builder:'onu'},
            'cto': {w:0.7, h:0.7, d:0.2, layout:'wall', label:'CTO', builder:'cto'},
            'converter': {w:0.5, h:0.12, d:0.35, layout:'mini', label:'Conversor', builder:'converter'},
            'camera': {w:0.35, h:0.35, d:0.35, layout:'generic', label:'Câmera', builder:'camera'},
            'sensor': {w:0.2, h:0.2, d:0.2, layout:'generic', label:'Sensor', builder:'sensor'},
            'telefone_ip': {w:0.35, h:0.25, d:0.15, layout:'generic', label:'Tel IP', builder:'phone'},
            'ata': {w:0.4, h:0.15, d:0.25, layout:'mini', label:'ATA', builder:'converter'},
            'nobreak_strip': {w:0.6, h:0.3, d:0.35, layout:'generic', label:'Fonte', builder:'ups'}
        };
        function getCatalog(t) { return DEVICE_CATALOG[t] || {w:0.5, h:0.35, d:0.4, layout:'generic', label:t || 'Disp', builder:'generic'}; }
        
        const S = {
            scene: null, camera: null, renderer: null, controls: null,
            raycaster: new THREE.Raycaster(), mouse: new THREE.Vector2(),
            floorPlane: new THREE.Plane(new THREE.Vector3(0,1,0), 2.5),
            devicesGroup: null, cablesGroup: null, particlesGroup: null,
            instances: [], connections: [], selected: null,
            dragging: null, dragStart: null, dragMoved: false, pointerDownPos: null,
            cableAnims: [], animFrame: null, isOpen: false,
            cableType: 'cat6', patchSource: null, patchDests: new Set()
        };
        const FLOOR_Y = -2.5;
        const RACK_BOTTOM = -2.35;
        const RACK_TOP = 7.5;
        const RACK_FP = 1.8;
        
        function makeChassis(w, h, d, color) {
            const m = new THREE.Mesh(
                new THREE.BoxGeometry(w, h, d),
                new THREE.MeshStandardMaterial({color: color || 0x1e293b, metalness: 0.7, roughness: 0.35})
            );
            m.castShadow = true;
            m.receiveShadow = true;
            return m;
        }
        
        function createDeviceTexture(type, label, powered) {
            const cv = document.createElement('canvas');
            cv.width = 512;
            cv.height = 128;
            const c = cv.getContext('2d');
            c.fillStyle = '#0f172a';
            c.fillRect(0, 0, 512, 128);
            c.strokeStyle = '#334155';
            c.lineWidth = 2;
            c.strokeRect(1, 1, 510, 126);
            c.fillStyle = '#1e293b';
            c.fillRect(0, 0, 512, 22);
            c.fillStyle = '#38bdf8';
            c.font = 'bold 11px monospace';
            c.fillText(label.toUpperCase().substring(0, 30), 8, 15);
            c.fillStyle = powered ? '#22c55e' : '#475569';
            c.beginPath();
            c.arc(500, 11, 4, 0, Math.PI * 2);
            c.fill();
            switch (type) {
                case 'switch':
                    for (let row = 0; row < 2; row++) {
                        for (let i = 0; i < 12; i++) {
                            const x = 12 + i*35, y = 32 + row*44;
                            c.fillStyle = '#020617';
                            c.fillRect(x, y, 28, 32);
                            c.strokeStyle = '#334155';
                            c.strokeRect(x, y, 28, 32);
                            c.fillStyle = powered && Math.random() > 0.4 ? '#22c55e' : '#475569';
                            c.fillRect(x+10, y+3, 6, 4);
                        }
                    }
                    for (let i = 0; i < 2; i++) {
                        c.fillStyle = '#020617';
                        c.fillRect(438 + i*36, 40, 30, 30);
                        c.strokeStyle = powered ? '#f59e0b' : '#334155';
                        c.strokeRect(438 + i*36, 40, 30, 30);
                    }
                    break;
                case 'olt':
                    for (let i = 0; i < 16; i++) {
                        c.fillStyle = '#020617';
                        c.fillRect(70 + i*26, 40, 20, 22);
                        c.strokeStyle = powered ? '#14b8a6' : '#334155';
                        c.strokeRect(70 + i*26, 40, 20, 22);
                    }
                    c.fillStyle = powered ? '#22c55e' : '#ef4444';
                    c.font = 'bold 12px monospace';
                    c.fillText(powered ? 'ONLINE' : 'OFF', 400, 60);
                    break;
                case 'onu':
                    c.fillStyle = '#22c55e';
                    c.font = 'bold 9px monospace';
                    c.fillText('PON', 15, 30);
                    c.fillStyle = '#020617';
                    c.fillRect(15, 38, 28, 24);
                    c.strokeStyle = powered ? '#22c55e' : '#334155';
                    c.strokeRect(15, 38, 28, 24);
                    for (let i = 0; i < 4; i++) {
                        c.fillStyle = '#020617';
                        c.fillRect(70 + i*30, 38, 24, 24);
                        c.strokeStyle = '#334155';
                        c.strokeRect(70 + i*30, 38, 24, 24);
                        c.fillStyle = powered ? '#22c55e' : '#334155';
                        c.fillRect(80 + i*30, 42, 5, 4);
                    }
                    break;
                case 'cto':
                    c.fillStyle = '#1e293b';
                    c.fillRect(10, 10, 492, 108);
                    c.strokeStyle = '#475569';
                    c.lineWidth = 2;
                    c.strokeRect(10, 10, 492, 108);
                    c.fillStyle = '#475569';
                    c.fillRect(240, 60, 32, 8);
                    c.fillStyle = '#94a3b8';
                    c.font = 'bold 11px monospace';
                    c.fillText('CTO BOX', 200, 115);
                    break;
                case 'converter':
                    c.fillStyle = '#10b981';
                    c.font = 'bold 9px monospace';
                    c.fillText('FX', 60, 55);
                    c.fillStyle = '#020617';
                    c.fillRect(90, 45, 40, 35);
                    c.strokeStyle = powered ? '#10b981' : '#334155';
                    c.strokeRect(90, 45, 40, 35);
                    c.fillStyle = '#94a3b8';
                    c.fillText('TX', 200, 55);
                    c.fillStyle = '#020617';
                    c.fillRect(230, 45, 40, 35);
                    c.strokeStyle = '#334155';
                    c.strokeRect(230, 45, 40, 35);
                    break;
                case 'nvr':
                    for (let i = 0; i < 4; i++) {
                        const x = 20 + i*60;
                        c.fillStyle = '#020617';
                        c.fillRect(x, 35, 50, 62);
                        c.strokeStyle = '#475569';
                        c.strokeRect(x, 35, 50, 62);
                        c.fillStyle = '#94a3b8';
                        c.font = 'bold 9px monospace';
                        c.fillText('HDD ' + (i+1), x+12, 55);
                    }
                    c.fillStyle = powered ? '#22c55e' : '#ef4444';
                    c.font = 'bold 12px monospace';
                    c.fillText(powered ? 'REC 16CH' : 'STANDBY', 280, 60);
                    break;
                case 'pbx':
                    c.fillStyle = '#a855f7';
                    c.font = 'bold 9px monospace';
                    c.fillText('FXS', 20, 32);
                    for (let i = 0; i < 8; i++) {
                        c.fillStyle = '#020617';
                        c.fillRect(20 + i*22, 38, 18, 28);
                        c.strokeStyle = powered ? '#a855f7' : '#334155';
                        c.strokeRect(20 + i*22, 38, 18, 28);
                    }
                    c.fillStyle = '#eab308';
                    c.fillText('FXO', 210, 32);
                    for (let i = 0; i < 4; i++) {
                        c.fillStyle = '#020617';
                        c.fillRect(210 + i*22, 38, 18, 28);
                        c.strokeStyle = powered ? '#eab308' : '#334155';
                        c.strokeRect(210 + i*22, 38, 18, 28);
                    }
                    break;
                case 'ups':
                    c.fillStyle = '#020617';
                    c.fillRect(20, 30, 300, 72);
                    c.strokeStyle = powered ? '#22c55e' : '#ef4444';
                    c.lineWidth = 2;
                    c.strokeRect(20, 30, 300, 72);
                    c.fillStyle = powered ? '#22c55e' : '#ef4444';
                    c.font = 'bold 20px monospace';
                    c.fillText(powered ? '220V · 87%' : '--- OFF ---', 40, 70);
                    break;
                case 'server':
                    for (let i = 0; i < 8; i++) {
                        const x = 15 + i*55;
                        c.fillStyle = '#020617';
                        c.fillRect(x, 35, 48, 62);
                        c.strokeStyle = '#475569';
                        c.strokeRect(x, 35, 48, 62);
                        c.fillStyle = '#94a3b8';
                        c.font = 'bold 8px monospace';
                        c.fillText('B' + (i+1), x+20, 45);
                    }
                    break;
                case 'nas':
                    for (let row = 0; row < 2; row++) {
                        for (let i = 0; i < 6; i++) {
                            const x = 15 + i*55, y = 30 + row*36;
                            c.fillStyle = '#020617';
                            c.fillRect(x, y, 48, 32);
                            c.strokeStyle = '#475569';
                            c.strokeRect(x, y, 48, 32);
                        }
                    }
                    break;
                case 'patch':
                    for (let i = 0; i < 24; i++) {
                        c.fillStyle = '#020617';
                        c.fillRect(12 + i*20, 45, 16, 32);
                        c.strokeStyle = '#475569';
                        c.strokeRect(12 + i*20, 45, 16, 32);
                        c.fillStyle = '#94a3b8';
                        c.font = 'bold 8px monospace';
                        c.fillText((i+1).toString(), 16 + i*20, 90);
                    }
                    break;
                case 'router':
                    for (let i = 0; i < 4; i++) {
                        const x = 20 + i*44;
                        c.fillStyle = '#020617';
                        c.fillRect(x, 70, 36, 30);
                        c.strokeStyle = '#0ea5e9';
                        c.strokeRect(x, 70, 36, 30);
                    }
                    c.fillStyle = '#020617';
                    c.fillRect(220, 70, 50, 30);
                    c.strokeStyle = '#f59e0b';
                    c.strokeRect(220, 70, 50, 30);
                    c.fillStyle = '#020617';
                    c.fillRect(700, 65, 180, 55);
                    c.fillStyle = powered ? '#22c55e' : '#ef4444';
                    c.font = 'bold 14px monospace';
                    c.fillText(powered ? 'WAN: UP' : 'WAN: DOWN', 720, 90);
                    break;
                case 'camera':
                    c.fillStyle = '#1e293b';
                    c.beginPath();
                    c.arc(256, 64, 40, 0, Math.PI * 2);
                    c.fill();
                    c.fillStyle = '#020617';
                    c.beginPath();
                    c.arc(256, 64, 22, 0, Math.PI * 2);
                    c.fill();
                    c.fillStyle = powered ? '#3b82f6' : '#334155';
                    c.beginPath();
                    c.arc(256, 64, 14, 0, Math.PI * 2);
                    c.fill();
                    break;
                case 'sensor':
                    c.fillStyle = '#475569';
                    c.beginPath();
                    c.arc(256, 64, 30, 0, Math.PI * 2);
                    c.fill();
                    c.fillStyle = powered ? '#dc3545' : '#475569';
                    c.beginPath();
                    c.arc(256, 64, 10, 0, Math.PI * 2);
                    c.fill();
                    break;
                case 'phone':
                    c.fillStyle = '#1e293b';
                    c.fillRect(200, 30, 112, 68);
                    c.fillStyle = '#020617';
                    c.fillRect(215, 40, 82, 30);
                    break;
                default:
                    c.fillStyle = '#020617';
                    c.fillRect(20, 30, 472, 68);
                    c.strokeStyle = '#475569';
                    c.strokeRect(20, 30, 472, 68);
                    c.fillStyle = powered ? '#22c55e' : '#ef4444';
                    c.font = 'bold 14px monospace';
                    c.fillText(powered ? '● ONLINE' : '○ OFF', 40, 68);
            }
            return new THREE.CanvasTexture(cv);
        }
        
        function buildDeviceModel(type, name, powered) {
            const cat = getCatalog(type);
            const g = new THREE.Group();
            g.add(makeChassis(cat.w, cat.h, cat.d, 0x1e293b));
            const tex = createDeviceTexture(cat.builder, cat.label, powered);
            const front = new THREE.Mesh(
                new THREE.PlaneGeometry(cat.w * 0.98, cat.h * 0.85),
                new THREE.MeshStandardMaterial({map: tex, roughness: 0.6, metalness: 0.2})
            );
            front.position.z = cat.d/2 + 0.005;
            g.add(front);
            if (cat.builder === 'router') {
                for (let i = 0; i < 3; i++) {
                    const ant = new THREE.Mesh(
                        new THREE.CylinderGeometry(0.02, 0.03, 0.6, 6),
                        new THREE.MeshStandardMaterial({color: 0x334155, metalness: 0.6})
                    );
                    ant.position.set(-0.8 + i*0.8, cat.h/2 + 0.3, -cat.d/2 + 0.3);
                    g.add(ant);
                }
            }
            if (cat.builder === 'onu') {
                const ant = new THREE.Mesh(
                    new THREE.CylinderGeometry(0.015, 0.02, 0.4, 6),
                    new THREE.MeshStandardMaterial({color: 0x334155})
                );
                ant.position.set(0, cat.h/2 + 0.2, -cat.d/2 + 0.15);
                g.add(ant);
            }
            const pwr = new THREE.Mesh(
                new THREE.SphereGeometry(Math.min(0.025, cat.h*0.15), 8, 8),
                new THREE.MeshStandardMaterial({color: 0x22c55e, emissive: 0x22c55e, emissiveIntensity: 1.2})
            );
            pwr.position.set(cat.w/2 - 0.1, cat.h/2 - 0.06, cat.d/2 + 0.02);
            g.add(pwr);
            return g;
        }
        
        function initScene() {
            const cont = document.getElementById('sim3d-container');
            cont.innerHTML = '';
            S.scene = new THREE.Scene();
            S.scene.background = new THREE.Color(0x080b13);
            S.scene.fog = new THREE.FogExp2(0x080b13, 0.012);
            S.camera = new THREE.PerspectiveCamera(45, window.innerWidth/window.innerHeight, 0.1, 200);
            S.camera.position.set(16, 8, 20);
            S.renderer = new THREE.WebGLRenderer({antialias: true, powerPreference: 'high-performance'});
            S.renderer.setSize(window.innerWidth, window.innerHeight);
            S.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            S.renderer.shadowMap.enabled = true;
            cont.appendChild(S.renderer.domElement);
            S.controls = new THREE.OrbitControls(S.camera, S.renderer.domElement);
            S.controls.enableDamping = true;
            S.controls.dampingFactor = 0.06;
            S.controls.target.set(0, 2.5, 0);
            S.controls.maxPolarAngle = Math.PI/2 + 0.05;
            S.controls.minDistance = 4;
            S.controls.maxDistance = 50;
            S.scene.add(new THREE.AmbientLight(0xffffff, 1.5));
            const spot = new THREE.SpotLight(0x38bdf8, 3);
            spot.position.set(12, 20, 14);
            spot.angle = Math.PI/4;
            spot.castShadow = true;
            S.scene.add(spot);
            const fill = new THREE.PointLight(0x0284c7, 2, 40);
            fill.position.set(-14, 10, -8);
            S.scene.add(fill);
            const floor = new THREE.Mesh(
                new THREE.PlaneGeometry(80, 80),
                new THREE.MeshStandardMaterial({color: 0x0a0e17, roughness: 0.5, metalness: 0.7})
            );
            floor.rotation.x = -Math.PI/2;
            floor.position.y = FLOOR_Y;
            floor.receiveShadow = true;
            S.scene.add(floor);
            const grid = new THREE.GridHelper(80, 80, 0x38bdf8, 0x1e293b);
            grid.position.y = FLOOR_Y + 0.01;
            grid.material.opacity = 0.35;
            grid.material.transparent = true;
            S.scene.add(grid);
            buildRack();
            S.devicesGroup = new THREE.Group();
            S.cablesGroup = new THREE.Group();
            S.particlesGroup = new THREE.Group();
            S.scene.add(S.devicesGroup);
            S.scene.add(S.cablesGroup);
            S.scene.add(S.particlesGroup);
            const dom = S.renderer.domElement;
            dom.addEventListener('pointerdown', onPointerDown);
            dom.addEventListener('pointermove', onPointerMove);
            dom.addEventListener('pointerup', onPointerUp);
            dom.addEventListener('dragover', onDragOver);
            dom.addEventListener('drop', onDrop);
            window.addEventListener('resize', onResize);
        }
        
        function buildRack() {
            const rack = new THREE.Group();
            const metal = new THREE.MeshStandardMaterial({color: 0x111622, metalness: 0.9, roughness: 0.4});
            const pil = new THREE.BoxGeometry(0.25, 10, 0.25);
            [[-2, 2.7, -2], [2, 2.7, -2], [-2, 2.7, 2], [2, 2.7, 2]].forEach(p => {
                const m = new THREE.Mesh(pil, metal);
                m.position.set(...p);
                m.castShadow = true;
                rack.add(m);
            });
            const top = new THREE.Mesh(new THREE.BoxGeometry(4.5, 0.3, 4.5), metal);
            top.position.set(0, 7.85, 0);
            rack.add(top);
            const bot = new THREE.Mesh(new THREE.BoxGeometry(4.5, 0.3, 4.5), metal);
            bot.position.set(0, -2.55, 0);
            rack.add(bot);
            S.scene.add(rack);
        }
        
        function rayToFloor(cx, cy) {
            const r = S.renderer.domElement.getBoundingClientRect();
            S.mouse.x = ((cx - r.left) / r.width) * 2 - 1;
            S.mouse.y = -((cy - r.top) / r.height) * 2 + 1;
            S.raycaster.setFromCamera(S.mouse, S.camera);
            const pt = new THREE.Vector3();
            S.raycaster.ray.intersectPlane(S.floorPlane, pt);
            return pt;
        }
        function rayDevices(cx, cy) {
            const r = S.renderer.domElement.getBoundingClientRect();
            S.mouse.x = ((cx - r.left) / r.width) * 2 - 1;
            S.mouse.y = -((cy - r.top) / r.height) * 2 + 1;
            S.raycaster.setFromCamera(S.mouse, S.camera);
            const hits = S.raycaster.intersectObjects(S.devicesGroup.children, true);
            if (!hits.length) return null;
            let obj = hits[0].object;
            while (obj.parent && obj.parent !== S.devicesGroup) obj = obj.parent;
            if (!obj.userData.instanceId) return null;
            return S.instances.find(i => i.id === obj.userData.instanceId) || null;
        }
        
        function computeY(x, z, h) {
            const inRack = Math.abs(x) < RACK_FP && Math.abs(z) < RACK_FP;
            if (!inRack) return FLOOR_Y + h/2 + 0.01;
            const inRackDevs = S.instances.filter(d => {
                const p = d.group.position;
                return Math.abs(p.x) < RACK_FP && Math.abs(p.z) < RACK_FP && p.y > FLOOR_Y - 0.5 && p.y < RACK_TOP;
            });
            if (inRackDevs.length === 0) return RACK_BOTTOM + h/2 + 0.05;
            let maxTop = RACK_BOTTOM;
            inRackDevs.forEach(d => {
                const t = d.group.position.y + d.h/2;
                if (t > maxTop) maxTop = t;
            });
            const newY = maxTop + h/2 + 0.06;
            return newY > RACK_TOP ? FLOOR_Y + h/2 + 0.01 : newY;
        }
        
        function addDevice(type, name, x, y, z, opts) {
            opts = opts || {};
            const cat = getCatalog(type);
            const g = buildDeviceModel(type, name, true);
            const finalY = (y === undefined || y === null) ? computeY(x, z, cat.h) : y;
            g.position.set(x, finalY, z);
            if (opts.rotation) g.rotation.y = opts.rotation;
            g.userData.instanceId = opts.restoreId || ('dev_' + Date.now() + '_' + Math.random().toString(36).slice(2,6));
            S.devicesGroup.add(g);
            const inst = {
                id: g.userData.instanceId, type, name, group: g,
                w: cat.w, h: cat.h, d: cat.d,
                ip: opts.ip || '', port: opts.port || 80,
                username: opts.username || '', password: opts.password || ''
            };
            S.instances.push(inst);
            rebuildCables();
            saveState();
            return inst;
        }
        
        function removeDevice(id) {
            const inst = S.instances.find(i => i.id === id);
            if (!inst) return;
            S.devicesGroup.remove(inst.group);
            inst.group.traverse(o => {
                if (o.geometry) o.geometry.dispose();
                if (o.material) {
                    if (o.material.map) o.material.map.dispose();
                    o.material.dispose();
                }
            });
            S.instances = S.instances.filter(i => i.id !== id);
            S.connections = S.connections.filter(c => c.from !== id && c.to !== id);
            if (S.selected && S.selected.id === id) {
                S.selected = null;
                hideProperties();
            }
            rebuildCables();
            renderConnPanel();
            saveState();
        }
        
        function rebuildCables() {
            while (S.cablesGroup.children.length) {
                const c = S.cablesGroup.children[0];
                S.cablesGroup.remove(c);
                if (c.geometry) c.geometry.dispose();
                if (c.material) c.material.dispose();
            }
            while (S.particlesGroup.children.length) {
                const c = S.particlesGroup.children[0];
                S.particlesGroup.remove(c);
                if (c.geometry) c.geometry.dispose();
                if (c.material) c.material.dispose();
            }
            S.cableAnims = [];
            S.connections.forEach(conn => {
                const from = S.instances.find(i => i.id === conn.from);
                const to = S.instances.find(i => i.id === conn.to);
                if (!from || !to) return;
                const isP = conn.cableType === 'power-ac';
                const z1 = isP ? -from.d/2 - 0.1 : from.d/2 + 0.1;
                const z2 = isP ? -to.d/2 - 0.1 : to.d/2 + 0.1;
                const p1 = new THREE.Vector3(from.group.position.x, from.group.position.y, from.group.position.z + z1);
                const p2 = new THREE.Vector3(to.group.position.x, to.group.position.y, to.group.position.z + z2);
                const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
                mid.y -= 0.3;
                mid.x += (isP ? -1 : 1);
                const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
                let color = 0x38bdf8, pcolor = 0x22c55e;
                if (conn.cableType === 'fiber-sfp') { color = 0xf59e0b; pcolor = 0xffffff; }
                else if (conn.cableType === 'power-ac') { color = 0xef4444; pcolor = 0xfacc15; }
                else if (conn.cableType === 'coax-bnc') { color = 0xa855f7; pcolor = 0x38bdf8; }
                S.cablesGroup.add(new THREE.Mesh(
                    new THREE.TubeGeometry(curve, 40, 0.04, 8, false),
                    new THREE.MeshStandardMaterial({color, roughness: 0.3, metalness: 0.2})
                ));
                const geo = new THREE.BufferGeometry();
                const count = 12;
                const pos = new Float32Array(count * 3);
                const prog = [];
                for (let i = 0; i < count; i++) {
                    prog.push(i / count);
                    const pt = curve.getPoint(i / count);
                    pos[i*3] = pt.x;
                    pos[i*3+1] = pt.y;
                    pos[i*3+2] = pt.z;
                }
                geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
                const pmesh = new THREE.Points(geo, new THREE.PointsMaterial({color: pcolor, size: 0.12, transparent: true, opacity: 0.9}));
                S.particlesGroup.add(pmesh);
                S.cableAnims.push({mesh: pmesh, curve, progress: prog});
            });
        }
        
        function renderConnPanel() {
            const panel = document.getElementById('sim3d-connections-panel');
            const list = document.getElementById('sim3d-connections-list');
            const cnt = document.getElementById('sim3d-connections-count');
            if (!list) return;
            list.innerHTML = '';
            cnt.innerText = S.connections.length;
            panel.style.display = S.connections.length > 0 ? 'flex' : 'none';
            S.connections.forEach(c => {
                const from = S.instances.find(x => x.id === c.from);
                const to = S.instances.find(x => x.id === c.to);
                const d = document.createElement('div');
                d.className = 'sim3d-connection-row';
                d.innerHTML = `<div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"><span class="tag">[${c.cableType.toUpperCase()}]</span> ${(from?.name || '?').substring(0,12)} ↔ ${(to?.name || '?').substring(0,12)}</div><button class="sim3d-connection-remove" onclick="sim3DRemoveConn('${c.id}')">✕</button>`;
                list.appendChild(d);
            });
        }
        window.sim3DRemoveConn = (id) => {
            S.connections = S.connections.filter(c => c.id !== id);
            rebuildCables();
            renderConnPanel();
            saveState();
        };
        
        function renderDrawer() {
            const list = document.getElementById('sim3d-equipment-list');
            if (!list) return;
            list.innerHTML = '';
            const grouped = {};
            Object.entries(categories || {}).forEach(([cat, data]) => {
                if (!data.devices) return;
                data.devices.forEach(d => {
                    if (!grouped[cat]) grouped[cat] = [];
                    grouped[cat].push(d);
                });
            });
            (customDevices || []).forEach(d => {
                if (!grouped['Personalizados']) grouped['Personalizados'] = [];
                grouped['Personalizados'].push(d);
            });
            Object.entries(grouped).forEach(([catName, devs]) => {
                const g = document.createElement('div');
                g.className = 'sim3d-eq-group';
                g.innerHTML = `<div class="sim3d-eq-group-title">${catName}</div>`;
                devs.forEach(dev => {
                    const cat = getCatalog(dev.type);
                    const lbl = {rack:'Rack', desktop:'Desktop', wall:'Parede', mini:'Mini', generic:'Compacto'}[cat.layout] || 'Custom';
                    const item = document.createElement('div');
                    item.className = 'sim3d-eq-item';
                    item.draggable = true;
                    item.innerHTML = `<div class="sim3d-eq-info"><div class="sim3d-eq-name"><span class="sim3d-eq-unit">${lbl}</span>${dev.name}</div><div class="sim3d-eq-desc">${dev.desc || dev.type || ''}</div></div>`;
                    item.addEventListener('dragstart', e => {
                        e.dataTransfer.setData('application/json', JSON.stringify({type: dev.type, name: dev.name}));
                        e.dataTransfer.effectAllowed = 'copy';
                        item.classList.add('dragging');
                    });
                    item.addEventListener('dragend', () => item.classList.remove('dragging'));
                    item.addEventListener('click', () => {
                        addDevice(dev.type, dev.name, -3, undefined, 4);
                        toast(`✅ ${dev.name} adicionado`);
                    });
                    g.appendChild(item);
                });
                list.appendChild(g);
            });
        }
        
        function onDragOver(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            const h = document.getElementById('sim3d-drop-hint');
            if (h) h.classList.add('active');
        }
        function onDrop(e) {
            e.preventDefault();
            const h = document.getElementById('sim3d-drop-hint');
            if (h) h.classList.remove('active');
            try {
                const data = JSON.parse(e.dataTransfer.getData('application/json'));
                if (!data) return;
                const pt = rayToFloor(e.clientX, e.clientY);
                addDevice(data.type, data.name, pt.x, undefined, pt.z);
                toast(`✅ ${data.name} posicionado`);
            } catch(err) { console.error(err); }
        }
        
        function onPointerDown(e) {
            if (e.button !== 0) return;
            S.pointerDownPos = {x: e.clientX, y: e.clientY};
            S.dragMoved = false;
            const hit = rayDevices(e.clientX, e.clientY);
            if (hit) {
                S.selected = hit;
                S.dragging = hit;
                S.dragStart = rayToFloor(e.clientX, e.clientY);
            } else {
                if (S.selected) {
                    S.selected = null;
                    hideProperties();
                }
            }
        }
        function onPointerMove(e) {
            if (S.pointerDownPos) {
                const dx = e.clientX - S.pointerDownPos.x;
                const dy = e.clientY - S.pointerDownPos.y;
                if (Math.hypot(dx, dy) > 5 && S.dragging && !S.dragMoved) {
                    S.dragMoved = true;
                    S.controls.enabled = false;
                    S.renderer.domElement.style.cursor = 'grabbing';
                }
            }
            if (S.dragging && S.dragMoved) {
                const cur = rayToFloor(e.clientX, e.clientY);
                S.dragging.group.position.x += cur.x - S.dragStart.x;
                S.dragging.group.position.z += cur.z - S.dragStart.z;
                S.dragStart = cur;
                S.dragging.group.position.y = computeY(S.dragging.group.position.x, S.dragging.group.position.z, S.dragging.h);
                rebuildCables();
            } else {
                const hit = rayDevices(e.clientX, e.clientY);
                S.renderer.domElement.style.cursor = hit ? 'grab' : 'default';
            }
        }
        function onPointerUp(e) {
            if (S.pointerDownPos) {
                const dx = e.clientX - S.pointerDownPos.x;
                const dy = e.clientY - S.pointerDownPos.y;
                const wasClick = Math.hypot(dx, dy) < 5;
                if (S.selected && wasClick) {
                    showProperties(S.selected);
                } else if (S.selected) {
                    saveState();
                }
            }
            S.dragging = null;
            S.dragMoved = false;
            S.pointerDownPos = null;
            S.controls.enabled = true;
            S.renderer.domElement.style.cursor = 'default';
        }
        function onResize() {
            if (!S.camera || !S.renderer) return;
            S.camera.aspect = window.innerWidth/window.innerHeight;
            S.camera.updateProjectionMatrix();
            S.renderer.setSize(window.innerWidth, window.innerHeight);
        }
        
        function showProperties(inst) {
            const panel = document.getElementById('sim3d-properties');
            const title = document.getElementById('sim3d-prop-title');
            const body = document.getElementById('sim3d-prop-body');
            if (!panel || !body) return;
            title.textContent = inst.name;
            const p = inst.group.position;
            body.innerHTML = `
                <div class="sim3d-prop-section"><div class="sim3d-prop-label">Nome</div><input class="sim3d-prop-input" id="s3d-name" value="${(inst.name || '').replace(/"/g, '&quot;')}"></div>
                <div class="sim3d-prop-section"><div class="sim3d-prop-label">Tipo</div><input class="sim3d-prop-input" value="${inst.type}" disabled></div>
                <div class="sim3d-prop-section"><div class="sim3d-prop-label">Posição</div><div class="sim3d-prop-row"><input class="sim3d-prop-input" id="s3d-x" type="number" step="0.1" value="${p.x.toFixed(2)}"><input class="sim3d-prop-input" id="s3d-y" type="number" step="0.1" value="${p.y.toFixed(2)}"></div><input class="sim3d-prop-input" id="s3d-z" type="number" step="0.1" value="${p.z.toFixed(2)}"></div>
                <div class="sim3d-prop-section"><div class="sim3d-prop-label">Rotação</div><input class="sim3d-prop-input" id="s3d-rot" type="range" min="0" max="360" value="${(inst.group.rotation.y * 180 / Math.PI).toFixed(0)}"></div>
                <div class="sim3d-prop-section"><div class="sim3d-prop-label">🌐 IP</div><input class="sim3d-prop-input" id="s3d-ip" value="${inst.ip || ''}" placeholder="192.168.1.100"></div>
                <div class="sim3d-prop-section"><div class="sim3d-prop-label">🔌 Porta</div><input class="sim3d-prop-input" id="s3d-port" type="number" value="${inst.port || 80}"></div>
                <div class="sim3d-prop-row"><div class="sim3d-prop-section"><div class="sim3d-prop-label">👤 User</div><input class="sim3d-prop-input" id="s3d-user" value="${inst.username || ''}"></div><div class="sim3d-prop-section"><div class="sim3d-prop-label">🔑 Pass</div><input class="sim3d-prop-input" id="s3d-pass" type="password" value="${inst.password || ''}"></div></div>
                <div class="sim3d-prop-actions">
                    <button class="sim3d-action-btn primary" onclick="s3dAccess('${inst.id}')">🌐 Acessar</button>
                    <button class="sim3d-action-btn" onclick="s3dOpenPatch('${inst.id}')">🔗 Conectar</button>
                    <button class="sim3d-action-btn" onclick="s3dRot('${inst.id}')">🔄 Girar</button>
                    <button class="sim3d-action-btn" onclick="s3dDup('${inst.id}')">📋 Duplicar</button>
                    <button class="sim3d-action-btn danger" onclick="s3dDel('${inst.id}')">🗑 Excluir</button>
                </div>
            `;
            const b = (id, ev, fn) => {
                const el = document.getElementById(id);
                if (el) el.addEventListener(ev, fn);
            };
            b('s3d-name', 'input', e => { inst.name = e.target.value; title.textContent = inst.name; saveState(); });
            b('s3d-x', 'change', e => { inst.group.position.x = parseFloat(e.target.value) || 0; rebuildCables(); saveState(); });
            b('s3d-y', 'change', e => { inst.group.position.y = parseFloat(e.target.value) || 0; rebuildCables(); saveState(); });
            b('s3d-z', 'change', e => { inst.group.position.z = parseFloat(e.target.value) || 0; rebuildCables(); saveState(); });
            b('s3d-rot', 'input', e => { inst.group.rotation.y = (parseFloat(e.target.value) || 0) * Math.PI / 180; rebuildCables(); saveState(); });
            b('s3d-ip', 'input', e => { inst.ip = e.target.value; saveState(); });
            b('s3d-port', 'input', e => { inst.port = parseInt(e.target.value) || 80; saveState(); });
            b('s3d-user', 'input', e => { inst.username = e.target.value; saveState(); });
            b('s3d-pass', 'input', e => { inst.password = e.target.value; saveState(); });
            panel.classList.add('open');
        }
        function hideProperties() {
            document.getElementById('sim3d-properties').classList.remove('open');
        }
        window.sim3DCloseProperties = hideProperties;
        
        window.s3dAccess = (id) => {
            const inst = S.instances.find(i => i.id === id);
            if (!inst || !inst.ip) { toast('⚠️ Configure IP'); return; }
            let url = inst.ip.trim();
            if (!/^https?:\/\//i.test(url)) url = 'http://' + url;
            if (inst.port && inst.port !== 80 && inst.port !== 443) url += ':' + inst.port;
            window.open(url, '_blank');
            toast(`🌐 Abrindo ${inst.name}`);
        };
        window.s3dRot = (id) => {
            const inst = S.instances.find(i => i.id === id);
            if (!inst) return;
            inst.group.rotation.y += Math.PI/2;
            rebuildCables();
            saveState();
        };
        window.s3dDup = (id) => {
            const inst = S.instances.find(i => i.id === id);
            if (!inst) return;
            const p = inst.group.position;
            addDevice(inst.type, inst.name + ' (cópia)', p.x + 0.5, p.y, p.z + 0.5, {ip: inst.ip, port: inst.port, username: inst.username, password: inst.password, rotation: inst.group.rotation.y});
        };
        window.s3dDel = (id) => {
            if (!confirm('Excluir?')) return;
            removeDevice(id);
        };
        
        window.s3dOpenPatch = (fromId) => {
            S.patchSource = fromId;
            S.patchDests.clear();
            const from = S.instances.find(i => i.id === fromId);
            if (!from) return;
            document.getElementById('sim3d-patch-title').textContent = `Conectar: ${from.name}`;
            const dl = document.getElementById('sim3d-dest-list');
            dl.innerHTML = '';
            S.instances.forEach(inst => {
                if (inst.id === fromId) return;
                const lbl = document.createElement('label');
                lbl.className = 'sim3d-dest-item';
                lbl.innerHTML = `<span>${inst.name}</span><input type="checkbox" value="${inst.id}" onchange="window.s3dTogDest('${inst.id}')">`;
                dl.appendChild(lbl);
            });
            document.getElementById('sim3d-patch-modal').classList.add('open');
        };
        window.s3dTogDest = (id) => {
            if (S.patchDests.has(id)) S.patchDests.delete(id);
            else S.patchDests.add(id);
        };
        
        function setupPatchUI() {
            document.querySelectorAll('.sim3d-cable-btn').forEach(btn => {
                if (btn.dataset.bound) return;
                btn.dataset.bound = '1';
                btn.addEventListener('click', e => {
                    document.querySelectorAll('.sim3d-cable-btn').forEach(b => b.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                    S.cableType = e.currentTarget.getAttribute('data-cable');
                });
            });
            const confirm = document.getElementById('sim3d-confirm-patch');
            if (confirm && !confirm.dataset.bound) {
                confirm.dataset.bound = '1';
                confirm.addEventListener('click', () => {
                    if (S.patchDests.size === 0) { toast('⚠️ Selecione destino'); return; }
                    let n = 0;
                    S.patchDests.forEach(destId => {
                        const exists = S.connections.some(c => (c.from === S.patchSource && c.to === destId) || (c.from === destId && c.to === S.patchSource));
                        if (!exists) {
                            S.connections.push({id: 'conn_' + Date.now() + '_' + Math.random().toString(36).slice(2,6), from: S.patchSource, to: destId, cableType: S.cableType});
                            n++;
                        }
                    });
                    document.getElementById('sim3d-patch-modal').classList.remove('open');
                    rebuildCables();
                    renderConnPanel();
                    saveState();
                    toast(`✅ ${n} conexão(ões)`);
                });
            }
            const close = document.getElementById('sim3d-patch-close');
            if (close && !close.dataset.bound) {
                close.dataset.bound = '1';
                close.addEventListener('click', () => document.getElementById('sim3d-patch-modal').classList.remove('open'));
            }
        }
        
        function saveState() {
            if (!currentUser) return;
            const devices = S.instances.map(d => ({
                id: d.id, type: d.type, name: d.name,
                x: d.group.position.x, y: d.group.position.y, z: d.group.position.z,
                rotation: d.group.rotation.y,
                ip: d.ip, port: d.port, username: d.username, password: d.password
            }));
            try {
                localStorage.setItem(STORAGE.SIM3D_DEV(currentUser), JSON.stringify(devices));
                localStorage.setItem(STORAGE.SIM3D_CONN(currentUser), JSON.stringify(S.connections));
            } catch(e) {}
        }
        window.saveSim3DState = saveState;
        
        function loadState() {
            if (!currentUser) return;
            try {
                const raw = localStorage.getItem(STORAGE.SIM3D_DEV(currentUser));
                if (raw) {
                    JSON.parse(raw).forEach(d => {
                        addDevice(d.type, d.name, d.x, d.y, d.z, {restoreId: d.id, rotation: d.rotation, ip: d.ip, port: d.port, username: d.username, password: d.password});
                    });
                }
                const rawC = localStorage.getItem(STORAGE.SIM3D_CONN(currentUser));
                if (rawC) {
                    S.connections = JSON.parse(rawC);
                    rebuildCables();
                    renderConnPanel();
                }
            } catch(e) {}
        }
        window.loadSim3DState = loadState;
        
        window.openSim3D = function() {
            document.getElementById('sim3d-overlay').classList.add('active');
            S.isOpen = true;
            S.instances = [];
            S.connections = [];
            S.selected = null;
            S.dragging = null;
            S.cableAnims = [];
            setTimeout(() => {
                initScene();
                setupPatchUI();
                setupListeners();
                loadState();
                renderDrawer();
                if (!S.animFrame) animate();
            }, 30);
        };
        window.closeSim3D = function() {
            document.getElementById('sim3d-overlay').classList.remove('active');
            S.isOpen = false;
            saveState();
            if (S.animFrame) {
                cancelAnimationFrame(S.animFrame);
                S.animFrame = null;
            }
            if (S.renderer) {
                S.renderer.dispose();
                if (S.renderer.domElement.parentNode) {
                    S.renderer.domElement.parentNode.removeChild(S.renderer.domElement);
                }
            }
            if (S.scene) {
                S.scene.traverse(o => {
                    if (o.geometry) o.geometry.dispose();
                    if (o.material) {
                        if (o.material.map) o.material.map.dispose();
                        o.material.dispose();
                    }
                });
                S.scene = null;
            }
            S.camera = null;
            S.renderer = null;
            S.controls = null;
            S.devicesGroup = null;
            S.cablesGroup = null;
            S.particlesGroup = null;
        };
        
        function setupListeners() {
            const b = (id, ev, fn) => {
                const el = document.getElementById(id);
                if (el && !el.dataset.bound) {
                    el.dataset.bound = '1';
                    el.addEventListener(ev, fn);
                }
            };
            b('sim3d-close-btn', 'click', () => window.closeSim3D());
            b('sim3d-toggle-drawer', 'click', () => document.getElementById('sim3d-equipment-drawer').classList.toggle('closed'));
            b('sim3d-close-drawer', 'click', () => document.getElementById('sim3d-equipment-drawer').classList.add('closed'));
            b('sim3d-run-script', 'click', runScript);
            b('sim3d-terminal-close', 'click', () => document.getElementById('sim3d-terminal').classList.remove('open'));
        }
        
        function runScript() {
            const modal = document.getElementById('sim3d-terminal');
            const out = document.getElementById('sim3d-terminal-output');
            modal.classList.add('open');
            out.innerHTML = '<p style="color:#64748b;">[SYSTEM] Executando diagnóstico...</p>';
            setTimeout(() => {
                const logs = [];
                logs.push(`<span style="color:#34d399;">[OK] ${S.instances.length} dispositivos no cenário.</span>`);
                logs.push(`<span style="color:#34d399;">[OK] ${S.connections.length} conexões estabelecidas.</span>`);
                if (S.instances.length === 0) logs.push('<span style="color:#fbbf24;">[ALERTA] Nenhum dispositivo.</span>');
                else {
                    const hasRouter = S.instances.some(i => i.type === 'router');
                    const hasSwitch = S.instances.some(i => i.type && i.type.startsWith('switch'));
                    const hasOLT = S.instances.some(i => i.type === 'olt');
                    const hasONU = S.instances.some(i => i.type === 'onu' || i.type === 'ont');
                    if (hasRouter) logs.push('<span style="color:#34d399;">[OK] Router detectado.</span>');
                    if (hasSwitch) logs.push('<span style="color:#34d399;">[OK] Switch(es).</span>');
                    if (hasOLT) logs.push('<span style="color:#34d399;">[OK] OLT GPON.</span>');
                    if (hasOLT && !hasONU) logs.push('<span style="color:#fbbf24;">[ALERTA] OLT sem ONU.</span>');
                    if (hasONU && !hasOLT) logs.push('<span style="color:#fbbf24;">[ALERTA] ONU sem OLT.</span>');
                }
                logs.push('<br><span style="color:#67e8f9;font-weight:bold;">>>> DIAGNÓSTICO CONCLUÍDO <<<</span>');
                out.innerHTML += logs.join('<br>');
                out.scrollTop = out.scrollHeight;
                toast('⚡ Diagnóstico concluído');
            }, 800);
        }
        
        function toast(msg) {
            const t = document.getElementById('sim3d-toast');
            const m = document.getElementById('sim3d-toast-message');
            if (!t || !m) return;
            m.innerText = msg;
            t.classList.add('show');
            clearTimeout(t._t);
            t._t = setTimeout(() => t.classList.remove('show'), 2800);
        }
        
        function animate() {
            S.animFrame = requestAnimationFrame(animate);
            S.cableAnims.forEach(a => {
                const arr = a.mesh.geometry.attributes.position.array;
                for (let i = 0; i < a.progress.length; i++) {
                    a.progress[i] += 0.008;
                    if (a.progress[i] > 1) a.progress[i] = 0;
                    const pt = a.curve.getPoint(a.progress[i]);
                    arr[i*3] = pt.x;
                    arr[i*3+1] = pt.y;
                    arr[i*3+2] = pt.z;
                }
                a.mesh.geometry.attributes.position.needsUpdate = true;
            });
            if (S.controls) S.controls.update();
            if (S.renderer && S.scene && S.camera) S.renderer.render(S.scene, S.camera);
        }
    })();
    
} catch(err) {
    console.error('[FATAL]', err);
    document.body.innerHTML = `<div style="color:white;background:#060d1a;padding:40px;font-family:monospace;min-height:100vh;"><h1 style="color:#ef4444;">⚠️ Erro no sistema</h1><p style="margin-top:20px;color:#94a3b8;">${err.message}</p><pre style="margin-top:20px;color:#67e8f9;background:#0f172a;padding:20px;border-radius:8px;overflow:auto;">${err.stack || ''}</pre></div>`;
}

</script>
</body>
</html>
"""

