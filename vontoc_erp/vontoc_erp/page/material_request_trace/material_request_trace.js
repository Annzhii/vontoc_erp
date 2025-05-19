frappe.pages['material-request-trace'].on_page_load = function(wrapper) {
    frappe.require("/assets/vontoc_erp/css/trace.css");

    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Material Request 流程追溯',
        single_column: true
    });

    // 页面 HTML
    $(page.body).html(`
        <div class="mb-3" style="width: 50%; margin: 0 auto; padding: 10px;">
    		<input type="text" id="trace-docname" class="form-control" placeholder="请输入 Material Request 编号（如 MAT-REQ-0001）">
			<button class="btn btn-primary mt-2" id="trace-btn">查看流程</button>
		</div>
		<div id="trace-result" style="width: 50%; margin: 20px auto 0;"></div>
    `);
	// 按钮点击事件
    $('#trace-btn').on('click', function () {
        const docname = $('#trace-docname').val();
        if (!docname) {
            frappe.msgprint("请输入编号");
            return;
        }

        frappe.call({
            method: 'vontoc_erp.api.material_request_trace.material_request_trace',
            args: { docname },
            callback: function (r) {
                if (r.message) {
                    const html = `<ul>${renderTree(r.message)}</ul>`;
                    $('#trace-result').html(html);
                } else {
                    $('#trace-result').html("<p>未找到相关流程数据。</p>");
                }
            }
        });
    });
};

// 渲染树结构 + 时间轴
function renderTree(node) {
    let html = `
        <li>
            <b>${node.type}</b>: 
            <a href="/app/${node.type.toLowerCase().replace(/ /g, "-")}/${node.name}" target="_blank">${node.name}</a> 
            <span class="workflow-state">(${node.workflow_state})</span>
            ${renderTimeline(node.history)}
        </li>
    `;

    if (node.children && node.children.length > 0) {
        html += "<ul>";
        node.children.forEach(child => {
            html += renderTree(child);
        });
        html += "</ul>";
    }

	if (node.so && node.so.length > 0) {
		node.so.forEach(so =>{
			html += renderTree(so)
		}); 
	}


    return html;
}

// 时间轴 HTML 生成（水平）
function renderTimeline(history) {
    if (!history || history.length === 0) return '';

    const items = history.map(h => `
        <div class="timeline-item">
            <div class="timeline-state">${h.workflow_state}</div>
            <div class="timeline-timestamp">${formatDate(h.timestamp)}</div>
        </div>
    `).join('<div class="timeline-arrow">==></div>');

    return `<div class="timeline-container">${items}</div>`;
}

// 时间格式
function formatDate(datetimeStr) {
    const d = new Date(datetimeStr);
    return `${d.getMonth()+1}-${d.getDate()} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
}
