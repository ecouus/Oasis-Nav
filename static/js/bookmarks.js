// 私密书签页 - 从 localStorage 获取 token（读取后立即删除，刷新即失效）

// 从 localStorage 获取 token 并立即删除
const token = localStorage.getItem('bookmark_token');
localStorage.removeItem('bookmark_token');  // 读取后立即删除，刷新即失效

// API 请求封装
function api(url, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(url, { ...options, headers });
}

// 检查权限并加载数据
async function init() {
    if (!token) {
        showError('权限不足');
        return;
    }
    
    // 尝试获取书签验证 token 是否有效
    try {
        const res = await api('/api/bookmarks');
        
        if (res.status === 401) {
            showError('权限不足或已过期');
            return;
        }
        
        const bookmarks = await res.json();
        renderBookmarks(bookmarks);
    } catch (err) {
        showError('加载失败');
    }
}

// 显示错误并跳转
function showError(msg) {
    const container = document.getElementById('bookmarkList');
    container.innerHTML = `<div class="empty-hint">${msg}，3秒后返回首页...</div>`;
    
    // 隐藏添加表单
    document.querySelector('.add-form').style.display = 'none';
    
    setTimeout(() => {
        window.location.href = '/';
    }, 3000);
}

// 加载书签列表
async function loadBookmarks() {
    try {
        const res = await api('/api/bookmarks');
        
        if (res.status === 401) {
            showError('权限已过期');
            return;
        }
        
        const bookmarks = await res.json();
        renderBookmarks(bookmarks);
    } catch (err) {
        console.error('加载书签失败', err);
    }
}

// 渲染书签列表
function renderBookmarks(bookmarks) {
    const container = document.getElementById('bookmarkList');
    
    if (!bookmarks || bookmarks.length === 0) {
        container.innerHTML = '<div class="empty-hint">暂无书签，点击上方添加</div>';
        return;
    }
    
    container.innerHTML = bookmarks.map(b => `
        <div class="bookmark-item" data-id="${b.id}">
            <a href="${escapeHtml(b.url)}" target="_blank" class="bookmark-link">
                <span class="bookmark-title">${escapeHtml(b.title)}</span>
                <span class="bookmark-url">${escapeHtml(b.url)}</span>
            </a>
            <button class="btn-delete" onclick="event.stopPropagation();deleteBookmark(${b.id})" title="删除">×</button>
        </div>
    `).join('');
}

// 添加书签
async function addBookmark() {
    const titleInput = document.getElementById('newTitle');
    const urlInput = document.getElementById('newUrl');
    const errorEl = document.getElementById('addError');
    
    const title = titleInput.value.trim();
    let url = urlInput.value.trim();
    
    errorEl.textContent = '';
    
    if (!title || !url) {
        errorEl.textContent = '请输入标题和链接';
        return;
    }
    
    // 自动补全 https://
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url;
    }
    
    try {
        const res = await api('/api/bookmarks', {
            method: 'POST',
            body: JSON.stringify({ title, url })
        });
        
        if (res.status === 401) {
            showError('权限已过期');
            return;
        }
        
        if (res.ok) {
            titleInput.value = '';
            urlInput.value = '';
            loadBookmarks();
        } else {
            const data = await res.json();
            errorEl.textContent = data.error || '添加失败';
        }
    } catch (err) {
        errorEl.textContent = '网络错误，请重试';
    }
}

// 删除书签
async function deleteBookmark(id) {
    if (!confirm('确定删除？')) return;
    
    try {
        const res = await api(`/api/bookmarks/${id}`, { method: 'DELETE' });
        
        if (res.status === 401) {
            showError('权限已过期');
            return;
        }
        
        if (res.ok) {
            loadBookmarks();
        }
    } catch (err) {
        console.error('删除失败', err);
    }
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 初始化
init();
