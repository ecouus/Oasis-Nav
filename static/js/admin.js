// ==================== 主题系统 ====================
(function() {
    // 加载保存的主题（和前台共享）
    const savedTheme = localStorage.getItem('nav-theme') || 'warm';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    // 更新主题按钮状态
    document.querySelectorAll('.theme-dot').forEach(dot => {
        dot.classList.toggle('active', dot.dataset.theme === savedTheme);
        
        dot.addEventListener('click', () => {
            const theme = dot.dataset.theme;
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('nav-theme', theme);
            document.querySelectorAll('.theme-dot').forEach(d => {
                d.classList.toggle('active', d.dataset.theme === theme);
            });
        });
    });
})();

// ==================== 全局状态 ====================
let token = localStorage.getItem('oasis_nav_token');
let categories = [];
let links = [];
let defaultCategoryId = null;

// ==================== Token 管理 ====================
// 检查 token 是否已过期
function isTokenExpired() {
    const expiresAt = localStorage.getItem('oasis_nav_token_expires');
    if (!expiresAt) return true;
    return Date.now() > parseInt(expiresAt);
}

// 保存 token 和过期时间
function saveToken(newToken, expiresIn) {
    token = newToken;
    localStorage.setItem('oasis_nav_token', newToken);
    const expiresAt = Date.now() + expiresIn * 1000;
    localStorage.setItem('oasis_nav_token_expires', expiresAt.toString());
}

// 清除 token
function clearToken() {
    token = null;
    localStorage.removeItem('oasis_nav_token');
    localStorage.removeItem('oasis_nav_token_expires');
}

// 初始化时检查 token 是否过期
if (token && isTokenExpired()) {
    clearToken();
}

// ==================== 安全函数 ====================
// HTML 转义，防止 XSS 攻击
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// 转义 HTML 属性值
function escapeAttr(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// ==================== 工具函数 ====================
async function api(url, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const res = await fetch(url, { ...options, headers });
    
    // 统一处理 401 认证错误（排除验证 token 的请求，避免循环）
    if (res.status === 401 && !url.includes('/api/verify-token')) {
        clearToken();
        showPanel('login');
    }
    
    return res;
}


// ==================== 初始化检查 ====================
async function checkAuth() {
    try {
        // 1. 检查是否已初始化（使用专门的 API，不会触发登录失败计数）
        const initCheck = await fetch('/api/check-init');
        const initData = await initCheck.json();
        
        if (initData.need_init) {
            showPanel('init');
            return;
        }
        
        // 2. 检查本地 token 是否过期
        if (token && isTokenExpired()) {
            clearToken();
        }
        
        // 3. 如果有 token，验证是否有效
        if (token) {
            const verifyRes = await api('/api/verify-token');
            if (verifyRes.status === 401) {
                clearToken();
            }
        }
        
        // 4. 根据 token 状态显示对应面板
        if (!token) {
            showPanel('login');
        } else {
            showPanel('admin');
            loadData();
        }
    } catch (err) {
        console.error('认证检查失败:', err);
        // 网络错误时显示登录面板
        showPanel('login');
    }
}

function showPanel(panel) {
    document.getElementById('initPanel').classList.add('hidden');
    document.getElementById('loginPanel').classList.add('hidden');
    document.getElementById('adminPanel').classList.add('hidden');
    document.getElementById(panel + 'Panel').classList.remove('hidden');
}

// ==================== 认证 ====================
async function initPassword(event) {
    const username = document.getElementById('initUsername').value.trim();
    const password = document.getElementById('initPassword').value;
    const confirm = document.getElementById('initPasswordConfirm').value;
    const errorEl = document.getElementById('initError');
    const btn = event.target;

    // 验证用户名：如果提供，必须至少3个字符
    if (username && username.length < 3) {
        errorEl.textContent = '用户名至少3个字符';
        return;
    }
    if (username && username.length > 32) {
        errorEl.textContent = '用户名最多32个字符';
        return;
    }

    if (password.length < 8 || !/[a-zA-Z]/.test(password) || !/[0-9]/.test(password)) {
        errorEl.textContent = '密码至少8位，需包含字母和数字';
        return;
    }
    if (password !== confirm) {
        errorEl.textContent = '两次密码不一致';
        return;
    }

    // 显示加载状态
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = '初始化中...';
    errorEl.textContent = '';

    try {
        // 发送初始化请求，用户名留空则传空字符串（后端会处理为默认admin）
        const res = await fetch('/api/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username || '', password })
        });

        if (res.ok) {
            // 显示登录中状态
            btn.textContent = '登录中...';
            
            // 自动登录（使用设置的用户名，如果留空则使用admin）
            const loginUsername = username || 'admin';
            const loginRes = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: loginUsername, password })
            });
            const data = await loginRes.json();
            
            // 检查登录是否成功
            if (loginRes.ok && data.token) {
                saveToken(data.token, data.expires_in);
                showPanel('admin');
                loadData();
            } else {
                // 登录失败，跳转到登录页面
                errorEl.textContent = '初始化成功，请登录';
                btn.disabled = false;
                btn.textContent = originalText;
                showPanel('login');
            }
        } else {
            const data = await res.json();
            errorEl.textContent = data.error || '初始化失败';
            btn.disabled = false;
            btn.textContent = originalText;
        }
    } catch (error) {
        errorEl.textContent = '网络错误，请重试';
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const errorEl = document.getElementById('loginError');
    const btn = document.querySelector('#loginPanel button');

    // 显示加载状态
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = '登录中...';
    errorEl.textContent = '';

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (res.ok) {
            saveToken(data.token, data.expires_in);
            showPanel('admin');
            loadData();
        } else {
            errorEl.textContent = data.error || '登录失败';
            btn.disabled = false;
            btn.textContent = originalText;
        }
    } catch (error) {
        errorEl.textContent = '网络错误，请重试';
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function logout() {
    clearToken();
    showPanel('login');
}

// ==================== 数据加载 ====================
async function loadData() {
    const [catRes, linkRes, defaultCatRes] = await Promise.all([
        api('/api/categories'),
        api('/api/links'),  // 后台登录后自动能看到所有链接
        fetch('/api/default-category')
    ]);

    categories = await catRes.json();
    links = await linkRes.json();
    const defaultCatData = await defaultCatRes.json();
    defaultCategoryId = defaultCatData.default_category_id;

    renderCategoriesTable();
    renderLinksTable();
    loadSiteSettings();  // 加载站点设置
    loadAdminPath();     // 加载后台路径设置
    loadAdminAccount();  // 加载管理账号设置
    loadSecuritySettings();  // 加载安全设置
    updateCategorySelects();
}

// ==================== 拖拽排序 ====================
let draggedRow = null;

function initDragSort(tbody, type) {
    const rows = tbody.querySelectorAll('tr[draggable="true"]');
    
    rows.forEach(row => {
        row.addEventListener('dragstart', (e) => {
            draggedRow = row;
            row.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });
        
        row.addEventListener('dragend', () => {
            row.classList.remove('dragging');
            document.querySelectorAll('.drag-over').forEach(r => r.classList.remove('drag-over'));
            draggedRow = null;
        });
        
        row.addEventListener('dragover', (e) => {
            e.preventDefault();
            // 链接只能在同分类内拖拽
            if (type === 'link' && row.dataset.category !== draggedRow?.dataset.category) {
                return;
            }
            if (row !== draggedRow) {
                row.classList.add('drag-over');
            }
        });
        
        row.addEventListener('dragleave', () => {
            row.classList.remove('drag-over');
        });
        
        row.addEventListener('drop', async (e) => {
            e.preventDefault();
            row.classList.remove('drag-over');
            
            // 链接只能在同分类内拖拽
            if (type === 'link' && row.dataset.category !== draggedRow?.dataset.category) {
                return;
            }
            
            if (draggedRow && row !== draggedRow) {
                // 移动行
                const draggedIndex = [...row.parentNode.children].indexOf(draggedRow);
                const targetIndex = [...row.parentNode.children].indexOf(row);
                
                if (draggedIndex < targetIndex) {
                    row.parentNode.insertBefore(draggedRow, row.nextSibling);
                } else {
                    row.parentNode.insertBefore(draggedRow, row);
                }
                
                // 保存新顺序
                await saveNewOrder(type);
            }
        });
    });
}

async function saveNewOrder(type) {
    const tbody = type === 'link' ? document.getElementById('linksTable') : document.getElementById('categoriesTable');
    const rows = tbody.querySelectorAll('tr[draggable="true"]');
    const orders = [];
    
    // 按分类分组计算排序（每个分类内从0开始）
    if (type === 'link') {
        const categoryOrders = {};
        rows.forEach(row => {
            const catId = row.dataset.category || 'uncategorized';
            if (!categoryOrders[catId]) categoryOrders[catId] = 0;
            orders.push({
                id: parseInt(row.dataset.id),
                sort_order: categoryOrders[catId]++
            });
        });
    } else {
        rows.forEach((row, index) => {
            orders.push({
                id: parseInt(row.dataset.id),
                sort_order: index
            });
        });
    }
    
    const endpoint = type === 'link' ? '/api/links/reorder' : '/api/categories/reorder';
    
    try {
        const res = await api(endpoint, {
            method: 'PUT',
            body: JSON.stringify({ orders })
        });
        
        if (res.ok) {
            // 更新本地数据
            loadData();
        }
    } catch (err) {
        console.error('保存排序失败', err);
    }
}

// ==================== Tab 切换 ====================
function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach((t, i) => {
        t.classList.toggle('active', t.textContent.includes(
            tabName === 'links' ? '链接' : tabName === 'categories' ? '分类' : '设置'
        ));
    });
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    document.getElementById('tab-' + tabName).classList.remove('hidden');
}

// ==================== 分类管理 ====================
function renderCategoriesTable() {
    const tbody = document.getElementById('categoriesTable');
    
    // 分离父分类和子分类
    const parentCategories = categories.filter(c => !c.parent_id);
    const childrenMap = {};
    categories.filter(c => c.parent_id).forEach(c => {
        if (!childrenMap[c.parent_id]) childrenMap[c.parent_id] = [];
        childrenMap[c.parent_id].push(c);
    });
    
    let html = '';
    
    // 按层级渲染：父分类 -> 子分类
    parentCategories.forEach(parent => {
        const isDefault = defaultCategoryId === parent.id;
        const defaultBadge = isDefault ? '<span class="badge badge-default">默认</span>' : '';
        const defaultBtn = isDefault 
            ? `<button class="btn btn-outline btn-sm" onclick="setDefaultCategory(null)" title="取消默认">取消默认</button>`
            : `<button class="btn btn-outline btn-sm" onclick="setDefaultCategory(${parent.id})" title="设为默认">设为默认</button>`;
        
        // 父分类行
        html += `
            <tr draggable="true" data-id="${parent.id}" data-type="category">
                <td class="drag-handle">⋮⋮</td>
                <td><strong>${escapeHtml(parent.name)}</strong> ${defaultBadge}</td>
                <td>-</td>
                <td class="actions">
                    ${defaultBtn}
                    <button class="btn btn-outline btn-sm" onclick="editCategory(${parent.id})">编辑</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteCategory(${parent.id})">删除</button>
                </td>
            </tr>
        `;
        
        // 子分类行（缩进显示）
        const children = childrenMap[parent.id] || [];
        children.forEach(child => {
            const isChildDefault = defaultCategoryId === child.id;
            const childDefaultBadge = isChildDefault ? '<span class="badge badge-default">默认</span>' : '';
            const childDefaultBtn = isChildDefault 
                ? `<button class="btn btn-outline btn-sm" onclick="setDefaultCategory(null)" title="取消默认">取消默认</button>`
                : `<button class="btn btn-outline btn-sm" onclick="setDefaultCategory(${child.id})" title="设为默认">设为默认</button>`;
            
            html += `
                <tr draggable="true" data-id="${child.id}" data-type="category" class="child-category">
                    <td class="drag-handle">⋮⋮</td>
                    <td style="padding-left: 30px;">↳ ${escapeHtml(child.name)} ${childDefaultBadge}</td>
                    <td>${escapeHtml(parent.name)}</td>
                    <td class="actions">
                        ${childDefaultBtn}
                        <button class="btn btn-outline btn-sm" onclick="editCategory(${child.id})">编辑</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteCategory(${child.id})">删除</button>
                    </td>
                </tr>
            `;
        });
    });
    
    tbody.innerHTML = html || '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">暂无分类</td></tr>';
    
    // 绑定拖拽事件
    initDragSort(tbody, 'category');
}

// 设置默认分类
async function setDefaultCategory(categoryId) {
    try {
        const res = await api('/api/default-category', {
            method: 'PUT',
            body: JSON.stringify({ category_id: categoryId })
        });
        
        if (res.ok) {
            defaultCategoryId = categoryId;
            renderCategoriesTable();
        } else if (res.status !== 401) {
            // 401 已在 api() 中处理，这里只处理其他错误
            const err = await res.json();
            alert(err.error || '设置失败');
        }
    } catch (err) {
        console.error('设置默认分类失败:', err);
        alert('网络错误，请重试');
    }
}

function updateCategorySelects() {
    const parentSelect = document.getElementById('categoryParent');
    const linkSelect = document.getElementById('linkCategory');

    parentSelect.innerHTML = '<option value="">无</option>' +
        categories.filter(c => !c.parent_id).map(c => 
            `<option value="${c.id}">${escapeHtml(c.name)}</option>`
        ).join('');

    linkSelect.innerHTML = '<option value="">未分类</option>' +
        categories.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
}

function showCategoryModal(id = null) {
    const modal = document.getElementById('categoryModal');
    document.getElementById('categoryModalTitle').textContent = id ? '编辑分类' : '添加分类';
    document.getElementById('categoryId').value = id || '';
    document.getElementById('categoryError').textContent = '';

    if (id) {
        const cat = categories.find(c => c.id === id);
        document.getElementById('categoryName').value = cat.name;
        document.getElementById('categoryParent').value = cat.parent_id || '';
        document.getElementById('categorySort').value = cat.sort_order;
    } else {
        document.getElementById('categoryName').value = '';
        document.getElementById('categoryParent').value = '';
        document.getElementById('categorySort').value = 0;
    }

    modal.classList.add('show');
}

function closeCategoryModal() {
    document.getElementById('categoryModal').classList.remove('show');
}

function editCategory(id) {
    showCategoryModal(id);
}

async function saveCategory() {
    const errorEl = document.getElementById('categoryError');
    errorEl.textContent = '';
    
    const id = document.getElementById('categoryId').value;
    const nameValue = document.getElementById('categoryName').value.trim();
    const parentValue = document.getElementById('categoryParent').value;
    const sortValue = document.getElementById('categorySort').value;
    
    const data = {
        name: nameValue,
        parent_id: parentValue ? parseInt(parentValue) : null,
        sort_order: parseInt(sortValue) || 0
    };

    if (!data.name) {
        errorEl.textContent = '请输入名称';
        return;
    }

    const url = id ? `/api/categories/${id}` : '/api/categories';
    const method = id ? 'PUT' : 'POST';

    try {
        const res = await api(url, { method, body: JSON.stringify(data) });

        if (res.ok) {
            closeCategoryModal();
            loadData();
        } else if (res.status !== 401) {
            // 401 已在 api() 中处理
            const err = await res.json();
            errorEl.textContent = err.error || '保存失败';
        }
    } catch (err) {
        console.error('保存分类失败:', err);
        errorEl.textContent = '网络错误，请重试';
    }
}

async function deleteCategory(id) {
    if (!confirm('确定删除此分类？该分类下的链接将变为未分类')) return;

    try {
        const res = await api(`/api/categories/${id}`, { method: 'DELETE' });
        if (res.ok) {
            loadData();
        } else if (res.status === 401) {
            // 401 已在 api 函数中处理
        } else {
            alert('删除失败');
        }
    } catch (err) {
        console.error('删除分类失败:', err);
        alert('网络错误，请重试');
    }
}

// ==================== 链接管理 ====================
function renderLinksTable() {
    const tbody = document.getElementById('linksTable');
    
    if (links.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">暂无链接</td></tr>';
        return;
    }
    
    // 按分类分组
    const linksByCategory = {};
    const uncategorized = [];
    
    links.forEach(link => {
        if (link.category_id) {
            if (!linksByCategory[link.category_id]) {
                linksByCategory[link.category_id] = [];
            }
            linksByCategory[link.category_id].push(link);
        } else {
            uncategorized.push(link);
        }
    });
    
    // 分离父分类和子分类
    const parentCategories = categories.filter(c => !c.parent_id);
    const childrenMap = {};
    categories.filter(c => c.parent_id).forEach(c => {
        if (!childrenMap[c.parent_id]) childrenMap[c.parent_id] = [];
        childrenMap[c.parent_id].push(c);
    });
    
    let html = '';
    
    // 按层级渲染：父分类 -> 子分类
    parentCategories.forEach(parent => {
        const parentLinks = linksByCategory[parent.id] || [];
        const children = childrenMap[parent.id] || [];
        
        // 计算该父分类及其子分类的总链接数
        let totalLinks = parentLinks.length;
        children.forEach(child => {
            totalLinks += (linksByCategory[child.id] || []).length;
        });
        
        // 如果没有任何链接则跳过
        if (totalLinks === 0) return;
        
        // 父分类标题行
        html += `
            <tr class="category-header">
                <td colspan="6" style="background:var(--bg-body);font-weight:600;color:var(--accent);padding:15px;">
                    📁 ${escapeHtml(parent.name)} (${totalLinks})
                </td>
            </tr>
        `;
        
        // 父分类下的直属链接
        parentLinks.forEach(link => {
            html += renderLinkRow(link);
        });
        
        // 子分类及其链接
        children.forEach(child => {
            const childLinks = linksByCategory[child.id] || [];
            if (childLinks.length === 0) return;
            
            // 子分类标题行（缩进）
            html += `
                <tr class="category-header child-category-header">
                    <td colspan="6" style="background:var(--bg-card);font-weight:500;color:var(--text-muted);padding:12px 15px 12px 35px;">
                        ↳ 📂 ${escapeHtml(child.name)} (${childLinks.length})
                    </td>
                </tr>
            `;
            
            // 子分类下的链接
            childLinks.forEach(link => {
                html += renderLinkRow(link, true);  // true 表示是子分类的链接
            });
        });
    });
    
    // 未分类的链接
    if (uncategorized.length > 0) {
        html += `
            <tr class="category-header">
                <td colspan="6" style="background:var(--bg-body);font-weight:600;color:var(--text-muted);padding:15px;">
                    📁 未分类 (${uncategorized.length})
                </td>
            </tr>
        `;
        uncategorized.forEach(link => {
            html += renderLinkRow(link);
        });
    }
    
    tbody.innerHTML = html;
    
    // 绑定拖拽事件
    initDragSort(tbody, 'link');
}

function renderLinkRow(link, isChild = false) {
    const indent = isChild ? 'style="padding-left: 35px;"' : '';
    return `
        <tr draggable="true" data-id="${link.id}" data-type="link" data-category="${link.category_id || ''}" class="${isChild ? 'child-link' : ''}">
            <td class="drag-handle">⋮⋮</td>
            <td ${indent}>${escapeHtml(link.title)}</td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                <a href="${escapeAttr(link.url)}" target="_blank" style="color:var(--accent)">${escapeHtml(link.url)}</a>
            </td>
            <td>
                <span class="badge ${link.is_hidden ? 'badge-hidden' : 'badge-visible'}">
                    ${link.is_hidden ? '隐藏' : '显示'}
                </span>
            </td>
            <td class="actions">
                <button class="btn btn-outline btn-sm" onclick="editLink(${link.id})">编辑</button>
                <button class="btn btn-danger btn-sm" onclick="deleteLink(${link.id})">删除</button>
            </td>
        </tr>
    `;
}

function showLinkModal(id = null) {
    const modal = document.getElementById('linkModal');
    document.getElementById('linkModalTitle').textContent = id ? '编辑链接' : '添加链接';
    document.getElementById('linkId').value = id || '';
    document.getElementById('linkError').textContent = '';

    if (id) {
        const link = links.find(l => l.id === id);
        document.getElementById('linkTitle').value = link.title;
        document.getElementById('linkUrl').value = link.url;
        document.getElementById('linkIcon').value = link.icon || '';
        document.getElementById('linkDescription').value = link.description || '';
        document.getElementById('linkCategory').value = link.category_id || '';
        document.getElementById('linkSort').value = link.sort_order;
        document.getElementById('linkHidden').checked = !!link.is_hidden;
    } else {
        document.getElementById('linkTitle').value = '';
        document.getElementById('linkUrl').value = '';
        document.getElementById('linkIcon').value = '';
        document.getElementById('linkDescription').value = '';
        // 新建链接时使用默认分类
        document.getElementById('linkCategory').value = defaultCategoryId || '';
        document.getElementById('linkSort').value = 0;
        document.getElementById('linkHidden').checked = false;
    }

    modal.classList.add('show');
}

function closeLinkModal() {
    document.getElementById('linkModal').classList.remove('show');
}

function editLink(id) {
    showLinkModal(id);
}

async function saveLink() {
    const errorEl = document.getElementById('linkError');
    errorEl.textContent = '';
    
    const id = document.getElementById('linkId').value;
    const data = {
        title: document.getElementById('linkTitle').value.trim(),
        url: document.getElementById('linkUrl').value.trim(),
        icon: document.getElementById('linkIcon').value || null,
        description: document.getElementById('linkDescription').value,
        category_id: document.getElementById('linkCategory').value || null,
        sort_order: parseInt(document.getElementById('linkSort').value) || 0,
        is_hidden: document.getElementById('linkHidden').checked
    };

    if (!data.title || !data.url) {
        errorEl.textContent = '标题和URL必填';
        return;
    }

    const url = id ? `/api/links/${id}` : '/api/links';
    const method = id ? 'PUT' : 'POST';
    
    // 获取保存按钮并显示加载状态
    const btn = document.querySelector('#linkModal .btn-primary');
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = '保存中...';

    try {
        const res = await api(url, { method, body: JSON.stringify(data) });

        if (res.ok) {
            closeLinkModal();
            loadData();
        } else if (res.status !== 401) {
            // 401 已在 api() 中处理
            const err = await res.json();
            errorEl.textContent = err.error || '保存失败';
        }
    } catch (err) {
        console.error('保存链接失败:', err);
        errorEl.textContent = '网络错误，请重试';
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function deleteLink(id) {
    if (!confirm('确定删除此链接？')) return;

    try {
        const res = await api(`/api/links/${id}`, { method: 'DELETE' });
        if (res.ok) {
            loadData();
        } else if (res.status === 401) {
            // 401 已在 api 函数中处理
        } else {
            alert('删除失败');
        }
    } catch (err) {
        console.error('删除链接失败:', err);
        alert('网络错误，请重试');
    }
}

// ==================== 设置 ====================

// 加载站点设置
async function loadSiteSettings() {
    try {
        const res = await fetch('/api/site-settings');
        const data = await res.json();
        
        document.getElementById('siteFavicon').value = data.favicon || '';
        document.getElementById('siteIcon').value = data.site_icon || '🥭';
        document.getElementById('siteTitle').value = data.site_title || 'Nav';
        document.getElementById('footerText').value = data.footer_text || '';
        document.getElementById('bookmarkHidden').checked = data.bookmark_hidden || false;
    } catch (err) {
        console.error('加载站点设置失败', err);
    }
}

// 保存站点设置
async function updateSiteSettings() {
    const errorEl = document.getElementById('siteSettingsError');
    const successEl = document.getElementById('siteSettingsSuccess');
    
    errorEl.textContent = '';
    successEl.classList.add('hidden');
    
    const data = {
        favicon: document.getElementById('siteFavicon').value.trim(),
        site_icon: document.getElementById('siteIcon').value || '🥭',
        site_title: document.getElementById('siteTitle').value || 'Nav',
        footer_text: document.getElementById('footerText').value,
        bookmark_hidden: document.getElementById('bookmarkHidden').checked
    };
    
    const res = await api('/api/site-settings', {
        method: 'PUT',
        body: JSON.stringify(data)
    });
    
    if (res.ok) {
        successEl.classList.remove('hidden');
        setTimeout(() => successEl.classList.add('hidden'), 3000);
    } else {
        const result = await res.json();
        errorEl.textContent = result.error || '保存失败';
    }
}

async function updateHiddenPassword() {
    const password = document.getElementById('newHiddenPassword').value;
    const errorEl = document.getElementById('settingsError');
    const successEl = document.getElementById('settingsSuccess');

    errorEl.textContent = '';
    successEl.classList.add('hidden');

    if (password.length < 4) {
        errorEl.textContent = '密码至少4位';
        return;
    }

    const res = await api('/api/config/hidden-password', {
        method: 'PUT',
        body: JSON.stringify({ password })
    });

    if (res.ok) {
        successEl.classList.remove('hidden');
        document.getElementById('newHiddenPassword').value = '';
        setTimeout(() => successEl.classList.add('hidden'), 3000);
    } else {
        const data = await res.json();
        errorEl.textContent = data.error || '更新失败';
    }
}

async function updateBookmarkPassword() {
    const password = document.getElementById('newBookmarkPassword').value;
    const errorEl = document.getElementById('bookmarkError');
    const successEl = document.getElementById('bookmarkSuccess');

    errorEl.textContent = '';
    successEl.classList.add('hidden');

    if (password.length < 8 || !/[a-zA-Z]/.test(password) || !/[0-9]/.test(password)) {
        errorEl.textContent = '密码至少8位，需包含字母和数字';
        return;
    }

    const res = await api('/api/config/bookmark-password', {
        method: 'PUT',
        body: JSON.stringify({ password })
    });

    if (res.ok) {
        successEl.classList.remove('hidden');
        document.getElementById('newBookmarkPassword').value = '';
        setTimeout(() => successEl.classList.add('hidden'), 3000);
    } else {
        const data = await res.json();
        errorEl.textContent = data.error || '更新失败';
    }
}

// 加载管理账号设置
async function loadAdminAccount() {
    try {
        const res = await api('/api/admin-account');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('adminUsername').value = data.username || 'admin';
        }
    } catch (err) {
        console.error('加载管理账号失败', err);
    }
}

// 保存管理账号设置
async function updateAdminAccount() {
    const errorEl = document.getElementById('accountError');
    const successEl = document.getElementById('accountSuccess');
    const username = document.getElementById('adminUsername').value.trim();
    const password = document.getElementById('adminNewPassword').value;
    
    errorEl.textContent = '';
    successEl.classList.add('hidden');
    
    if (!username || username.length < 3) {
        errorEl.textContent = '用户名至少3个字符';
        return;
    }
    
    if (password && (password.length < 8 || !/[a-zA-Z]/.test(password) || !/[0-9]/.test(password))) {
        errorEl.textContent = '密码至少8位，需包含字母和数字';
        return;
    }
    
    const data = { username };
    if (password) {
        data.password = password;
    }
    
    const res = await api('/api/admin-account', {
        method: 'PUT',
        body: JSON.stringify(data)
    });
    
    if (res.ok) {
        successEl.classList.remove('hidden');
        document.getElementById('adminNewPassword').value = '';
        setTimeout(() => successEl.classList.add('hidden'), 3000);
    } else {
        const result = await res.json();
        errorEl.textContent = result.error || '保存失败';
    }
}

// 加载后台路径设置
async function loadAdminPath() {
    try {
        const res = await api('/api/admin-path');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('adminPath').value = data.admin_path || '/admin';
        }
    } catch (err) {
        console.error('加载后台路径失败', err);
    }
}

// 保存后台路径
async function updateAdminPath() {
    const errorEl = document.getElementById('adminPathError');
    const successEl = document.getElementById('adminPathSuccess');
    let newPath = document.getElementById('adminPath').value.trim();
    
    errorEl.textContent = '';
    successEl.classList.add('hidden');
    
    if (!newPath) {
        errorEl.textContent = '路径不能为空';
        return;
    }
    
    // 自动补全前导斜杠
    if (!newPath.startsWith('/')) {
        newPath = '/' + newPath;
        document.getElementById('adminPath').value = newPath;
    }
    
    const res = await api('/api/admin-path', {
        method: 'PUT',
        body: JSON.stringify({ admin_path: newPath })
    });
    
    if (res.ok) {
        const data = await res.json();
        successEl.classList.remove('hidden');
        
        // 2秒后跳转到新路径
        setTimeout(() => {
            window.location.href = data.admin_path;
        }, 1500);
    } else {
        const data = await res.json();
        errorEl.textContent = data.error || '保存失败';
    }
}

// 加载安全设置
async function loadSecuritySettings() {
    try {
        const res = await api('/api/security-settings');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('ipBindingEnabled').checked = data.ip_binding_enabled || false;
        }
    } catch (err) {
        console.error('加载安全设置失败', err);
    }
}

// 保存安全设置
async function updateSecuritySettings() {
    const errorEl = document.getElementById('securityError');
    const successEl = document.getElementById('securitySuccess');
    const ipBindingEnabled = document.getElementById('ipBindingEnabled').checked;
    
    errorEl.textContent = '';
    successEl.classList.add('hidden');
    
    const res = await api('/api/security-settings', {
        method: 'PUT',
        body: JSON.stringify({ ip_binding_enabled: ipBindingEnabled })
    });
    
    if (res.ok) {
        successEl.classList.remove('hidden');
        setTimeout(() => successEl.classList.add('hidden'), 3000);
    } else {
        const result = await res.json();
        errorEl.textContent = result.error || '保存失败';
    }
}

// ==================== 点击弹窗外关闭 ====================
document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', e => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });
});

// ==================== 初始化 ====================
checkAuth();
