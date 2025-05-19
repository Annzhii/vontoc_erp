frappe.pages['mail-box'].on_page_load = function(wrapper) {
    // 清空内容，放一个挂载点
    wrapper.innerHTML = `<div id="app"></div>`;
  
    // 加载样式文件
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/frontend/assets/index.css';
    document.head.appendChild(link);
  
    // 加载脚本文件（模块类型）
    const script = document.createElement('script');
    script.type = 'module';
    script.src = '/frontend/assets/index.js';
    document.body.appendChild(script);
  };
  