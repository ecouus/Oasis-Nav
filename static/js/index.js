// ==================== 全局状态 ====================
let categories = [];
let links = [];
let hiddenToken = null;
let showingHidden = false;

// ==================== 主题系统 ====================
const themeToggle = document.getElementById('themeToggle');
const settingsPanel = document.getElementById('settingsPanel');
const themeBtns = document.querySelectorAll('.theme-btn');

// 加载保存的主题
function loadTheme() {
    const savedTheme = localStorage.getItem('nav-theme') || 'warm';
    const savedCss = localStorage.getItem('nav-custom-css') || '';
    
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeButtons(savedTheme);
    
    if (savedCss) {
        document.getElementById('customCss').value = savedCss;
        document.getElementById('customStyles').textContent = savedCss;
    }
}

// 更新主题按钮状态
function updateThemeButtons(theme) {
    themeBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === theme);
    });
}

// 切换设置面板
themeToggle.addEventListener('click', (e) => {
    e.stopPropagation();
    settingsPanel.classList.toggle('show');
});

// 点击外部关闭设置面板
document.addEventListener('click', (e) => {
    if (!settingsPanel.contains(e.target) && e.target !== themeToggle) {
        settingsPanel.classList.remove('show');
    }
});

// 主题按钮点击
themeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const theme = btn.dataset.theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('nav-theme', theme);
        updateThemeButtons(theme);
    });
});

// 应用自定义 CSS
function applyCustomCss() {
    const css = document.getElementById('customCss').value;
    document.getElementById('customStyles').textContent = css;
    localStorage.setItem('nav-custom-css', css);
}

// 初始化主题
loadTheme();

// ==================== 隐蔽触发器（双击调色盘显示隐藏链接，三击打开书签页） ====================
let clickCount = 0;
let clickTimer = null;

document.getElementById('themeToggle').addEventListener('click', function(e) {
    clickCount++;
    
    if (clickTimer) clearTimeout(clickTimer);
    
    clickTimer = setTimeout(() => {
        if (clickCount === 2) {
            // 双击 - 显示隐藏链接
            e.preventDefault();
            e.stopPropagation();
            showPasswordModal();
        } else if (clickCount >= 3) {
            // 三击 - 弹出书签密码框
            e.preventDefault();
            e.stopPropagation();
            showBookmarkModal();
        }
        clickCount = 0;
    }, 300);
});

// ==================== 返回顶部按钮 ====================
const backToTopBtn = document.getElementById('backToTop');

window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
        backToTopBtn.classList.add('show');
    } else {
        backToTopBtn.classList.remove('show');
    }
});

backToTopBtn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

document.getElementById('passwordModal').addEventListener('click', function(e) {
    if (e.target === this) {
        this.classList.remove('show');
        document.getElementById('passwordError').textContent = '';
    }
});

function showPasswordModal() {
    if (showingHidden) {
        showingHidden = false;
        hiddenToken = null;
        loadData();
        return;
    }
    document.getElementById('passwordModal').classList.add('show');
    document.getElementById('hiddenPassword').focus();
}

async function verifyHiddenPassword() {
    const password = document.getElementById('hiddenPassword').value;
    const errorEl = document.getElementById('passwordError');
    
    try {
        const res = await fetch('/api/verify-hidden', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });
        
        const data = await res.json();
        
        if (res.ok) {
            hiddenToken = data.token;
            showingHidden = true;
            document.getElementById('passwordModal').classList.remove('show');
            document.getElementById('hiddenPassword').value = '';
            errorEl.textContent = '';
            loadData();
            
            setTimeout(() => {
                if (showingHidden) {
                    showingHidden = false;
                    hiddenToken = null;
                    loadData();
                }
            }, data.expires_in * 1000);
        } else {
            errorEl.textContent = data.error || '验证失败';
        }
    } catch (err) {
        errorEl.textContent = '网络错误';
    }
}

// ==================== 书签密码验证 ====================
document.getElementById('bookmarkModal').addEventListener('click', function(e) {
    if (e.target === this) {
        this.classList.remove('show');
        document.getElementById('bookmarkError').textContent = '';
    }
});

function showBookmarkModal() {
    document.getElementById('bookmarkModal').classList.add('show');
    document.getElementById('bookmarkPassword').focus();
}

async function verifyBookmarkPassword() {
    const password = document.getElementById('bookmarkPassword').value;
    const errorEl = document.getElementById('bookmarkError');
    
    if (!password) {
        errorEl.textContent = '请输入密码';
        return;
    }
    
    try {
        const res = await fetch('/api/bookmarks/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });
        
        const data = await res.json();
        
        if (res.ok) {
            document.getElementById('bookmarkModal').classList.remove('show');
            document.getElementById('bookmarkPassword').value = '';
            errorEl.textContent = '';
            // 将 token 存入 localStorage（书签页读取后会立即删除）
            localStorage.setItem('bookmark_token', data.token);
            // 在当前标签页跳转到书签页
            window.location.href = '/bookmarks';
        } else {
            errorEl.textContent = data.error || '密码错误';
        }
    } catch (err) {
        errorEl.textContent = '网络错误';
    }
}

// ==================== 站点设置 ====================
async function loadSiteSettings() {
    try {
        const res = await fetch('/api/site-settings');
        const data = await res.json();
        
        document.getElementById('pageTitle').textContent = (data.site_title || 'Nav') + ' | 书签';
        
        if (data.favicon) {
            document.getElementById('favicon').href = data.favicon;
        }
        
        document.getElementById('siteIcon').textContent = data.site_icon || '🥭';
        document.getElementById('siteTitle').textContent = data.site_title || 'Nav';
        
        const footerCustom = document.getElementById('footerCustom');
        if (data.footer_text) {
            footerCustom.innerHTML = data.footer_text;  // 支持 HTML 超链接
            footerCustom.style.display = 'inline';
        } else {
            footerCustom.style.display = 'none';
        }
    } catch (err) {
        console.error('加载站点设置失败', err);
    }
}

// ==================== 数据加载 ====================
async function loadData() {
    try {
        const [catRes, linkRes] = await Promise.all([
            fetch('/api/categories'),
            fetch(showingHidden && hiddenToken 
                ? `/api/links?show_hidden=1&hidden_token=${hiddenToken}` 
                : '/api/links')
        ]);
        
        categories = await catRes.json();
        links = await linkRes.json();
        
        renderCategoryNav();
        renderContent();
    } catch (err) {
        document.getElementById('contentArea').innerHTML = 
            '<div class="empty-state">加载失败，请刷新重试</div>';
    }
}

// ==================== 渲染分类导航 ====================
function renderCategoryNav() {
    const container = document.getElementById('categoryNav');
    if (!container) return;
    
    // 分离父分类和子分类（使用 == 进行松散比较，避免类型问题）
    const parentCategories = categories.filter(c => !c.parent_id);
    const childrenMap = {};
    
    categories.filter(c => c.parent_id).forEach(c => {
        const pid = c.parent_id;
        if (!childrenMap[pid]) childrenMap[pid] = [];
        childrenMap[pid].push(c);
    });
    
    // 检查分类是否有链接（使用 == 进行松散比较）
    const hasLinks = (catId) => links.some(link => link.category_id == catId);
    
    // 检查父分类或其子分类是否有链接
    const parentHasLinks = (parentId) => {
        if (hasLinks(parentId)) return true;
        const children = childrenMap[parentId] || [];
        return children.some(child => hasLinks(child.id));
    };
    
    let html = '';
    let isFirst = true;
    
    parentCategories.forEach(parent => {
        // 跳过没有链接的父分类
        if (!parentHasLinks(parent.id)) return;
        
        const children = (childrenMap[parent.id] || []).filter(c => hasLinks(c.id));
        const parentSelfHasLinks = hasLinks(parent.id);
        
        if (children.length > 0) {
            // 有子分类 - 显示下拉菜单
            html += `
                <div class="category-item has-dropdown">
                    <button class="category-tab ${isFirst ? 'active' : ''}" data-id="${parent.id}">
                        ${parent.name}
                        <span class="arrow">▼</span>
                    </button>
                    <div class="category-dropdown">
                        ${parentSelfHasLinks ? `
                            <button class="category-dropdown-item" data-id="${parent.id}" 
                                    onclick="scrollToCategory(${parent.id}, this)">
                                全部${parent.name}
                            </button>
                        ` : ''}
                        ${children.map(child => `
                            <button class="category-dropdown-item" data-id="${child.id}"
                                    onclick="scrollToCategory(${child.id}, this)">
                                ${child.name}
                            </button>
                        `).join('')}
                    </div>
                </div>
            `;
        } else if (parentSelfHasLinks) {
            // 没有子分类 - 直接显示
            html += `
                <div class="category-item">
                    <button class="category-tab ${isFirst ? 'active' : ''}" data-id="${parent.id}"
                            onclick="scrollToCategory(${parent.id}, this)">
                        ${parent.name}
                    </button>
                </div>
            `;
        }
        
        if (isFirst && (children.length > 0 || parentSelfHasLinks)) {
            isFirst = false;
        }
    });
    
    container.innerHTML = html;
    
    // 调试：打印分类结构
    console.log('分类结构:', { parentCategories, childrenMap, links: links.slice(0, 5) });
}

// 滚动到指定分类
function scrollToCategory(categoryId, btn) {
    const section = document.getElementById(`section-${categoryId}`);
    if (section) {
        // 更新激活状态 - 所有标签和下拉项
        document.querySelectorAll('.category-tab, .category-dropdown-item').forEach(t => {
            t.classList.remove('active');
        });
        btn.classList.add('active');
        
        // 如果是下拉项，也高亮父标签
        const parentItem = btn.closest('.category-item');
        if (parentItem) {
            const parentTab = parentItem.querySelector('.category-tab');
            if (parentTab && parentTab !== btn) {
                parentTab.classList.add('active');
            }
        }
        
        // 平滑滚动
        const topOffset = 70;
        const elementPosition = section.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - topOffset;
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }
}

// ==================== 渲染内容 ====================
function renderContent() {
    const container = document.getElementById('contentArea');
    
    if (links.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无链接，请先在后台添加</div>';
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
        
        // 收集该父分类下所有链接（包括子分类的）
        let hasAnyLinks = parentLinks.length > 0;
        children.forEach(child => {
            if ((linksByCategory[child.id] || []).length > 0) {
                hasAnyLinks = true;
            }
        });
        
        // 如果没有任何链接则跳过
        if (!hasAnyLinks) return;
        
        html += `<section id="section-${parent.id}" class="section-container">`;
        
        // 父分类标题和直属链接
        if (parentLinks.length > 0) {
            html += `
                <h2 class="section-title">${parent.name}</h2>
                <div class="card-grid">
                    ${parentLinks.map(link => renderCard(link)).join('')}
                </div>
            `;
        } else if (children.length > 0) {
            // 父分类没有直属链接但有子分类，显示父分类标题
            html += `<h2 class="section-title">${parent.name}</h2>`;
        }
        
        // 子分类及其链接
        children.forEach(child => {
            const childLinks = linksByCategory[child.id] || [];
            if (childLinks.length === 0) return;
            
            html += `
                <div id="section-${child.id}" class="sub-section">
                    <h3 class="sub-section-title">${child.name}</h3>
                    <div class="card-grid">
                        ${childLinks.map(link => renderCard(link)).join('')}
                    </div>
                </div>
            `;
        });
        
        html += `</section>`;
    });
    
    // 渲染未分类的链接
    if (uncategorized.length > 0) {
        html += `
            <section id="section-uncategorized" class="section-container">
                <h2 class="section-title">未分类</h2>
                <div class="card-grid">
                    ${uncategorized.map(link => renderCard(link)).join('')}
                </div>
            </section>
        `;
    }
    
    container.innerHTML = html || '<div class="empty-state">暂无链接</div>';
}

// 规范化 URL
function normalizeUrl(url) {
    if (!url) return url;
    url = url.trim();
    if (!/^https?:\/\//i.test(url)) {
        return 'https://' + url;
    }
    return url;
}

// 提取域名
function getDomain(url) {
    try {
        return new URL(normalizeUrl(url)).hostname;
    } catch {
        return url.replace(/^(https?:\/\/)?/i, '').split('/')[0];
    }
}

// 渲染单个卡片
function renderCard(link) {
    const fullUrl = normalizeUrl(link.url);
    const domain = getDomain(link.url);
    const iconUrl = link.icon || `https://icons.duckduckgo.com/ip3/${domain}.ico`;
    const hiddenClass = link.is_hidden ? 'hidden-item' : '';
    const firstChar = link.title.charAt(0).toUpperCase();
    const tooltip = link.description || link.title;
    
    return `
        <a href="${fullUrl}" target="_blank" class="nav-card ${hiddenClass}" 
           data-title="${link.title}" data-desc="${link.description || ''}">
            <img class="icon" src="${iconUrl}" alt="" 
                 onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
            <div class="icon-fallback" style="display:none;">${firstChar}</div>
            <span class="title">${link.title}</span>
            <div class="tooltip">${tooltip}</div>
        </a>
    `;
}

// ==================== 搜索过滤 ====================
function filterLinks() {
    const filter = document.getElementById('searchInput').value.toUpperCase();
    const cards = document.querySelectorAll('.nav-card');
    const sections = document.querySelectorAll('.section-container');

    cards.forEach(card => {
        const title = card.dataset.title || '';
        const desc = card.dataset.desc || '';
        
        if (title.toUpperCase().includes(filter) || desc.toUpperCase().includes(filter)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });

    sections.forEach(section => {
        const visibleCards = section.querySelectorAll('.nav-card:not([style*="display: none"])');
        section.style.display = visibleCards.length === 0 ? 'none' : 'block';
    });
}

// ==================== 滚动监听 - 更新分类导航激活状态 ====================
let scrollTimeout;
window.addEventListener('scroll', () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
        updateActiveCategoryOnScroll();
    }, 50);
});

function updateActiveCategoryOnScroll() {
    const sections = document.querySelectorAll('.section-container');
    
    if (sections.length === 0) return;
    
    const scrollPos = window.scrollY + 100;
    let activeId = null;
    
    // 找到当前可见的分类
    sections.forEach(section => {
        const top = section.offsetTop;
        const bottom = top + section.offsetHeight;
        
        if (scrollPos >= top && scrollPos < bottom) {
            activeId = section.id.replace('section-', '');
        }
    });
    
    if (!activeId) return;
    
    // 清除所有激活状态
    document.querySelectorAll('.category-tab, .category-dropdown-item').forEach(el => {
        el.classList.remove('active');
    });
    
    // 激活对应的标签或下拉项
    const activeDropdownItem = document.querySelector(`.category-dropdown-item[data-id="${activeId}"]`);
    const activeTab = document.querySelector(`.category-tab[data-id="${activeId}"]`);
    
    if (activeDropdownItem) {
        activeDropdownItem.classList.add('active');
        // 同时高亮父标签
        const parentItem = activeDropdownItem.closest('.category-item');
        if (parentItem) {
            const parentTab = parentItem.querySelector('.category-tab');
            if (parentTab) parentTab.classList.add('active');
        }
    } else if (activeTab) {
        activeTab.classList.add('active');
    } else {
        // 可能是子分类，找到其父分类的标签
        const category = categories.find(c => c.id == activeId);
        if (category && category.parent_id) {
            const parentTab = document.querySelector(`.category-tab[data-id="${category.parent_id}"]`);
            if (parentTab) parentTab.classList.add('active');
        }
    }
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    loadSiteSettings();
    loadData();
});
