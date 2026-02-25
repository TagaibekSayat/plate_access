function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function buildQueryFromForm(form) {
    const params = new URLSearchParams(new FormData(form));
    if (params.get("use_date") !== "1") {
        params.delete("log_date");
    }
    return params;
}

function renderPagination(container, payload, queryBase) {
    const { current_page: currentPage, visible_pages: visiblePages, total_pages: totalPages } = payload;
    const html = [];

    if (container.id === "pagination-bottom" && currentPage > 1) {
        const prev = new URLSearchParams(queryBase);
        prev.set("page", String(currentPage - 1));
        html.push(`<a href="/logs?${prev.toString()}">вЂ№</a>`);
    }

    visiblePages.forEach((p) => {
        if (p === currentPage) {
            html.push(`<span class="active">${p}</span>`);
        } else {
            const linkParams = new URLSearchParams(queryBase);
            linkParams.set("page", String(p));
            html.push(`<a href="/logs?${linkParams.toString()}">${p}</a>`);
        }
    });

    if (container.id === "pagination-bottom" && currentPage < totalPages) {
        const next = new URLSearchParams(queryBase);
        next.set("page", String(currentPage + 1));
        html.push(`<a href="/logs?${next.toString()}">вЂє</a>`);
    }

    container.innerHTML = html.join("");
}

async function refreshLogs() {
    const form = document.getElementById("logs-filter-form");
    if (!form) return;

    const params = buildQueryFromForm(form);
    const pageInput = form.querySelector('input[name="page"]');
    if (pageInput && !params.get("page")) {
        params.set("page", pageInput.value || "1");
    }

    const response = await fetch(`/api/logs?${params.toString()}`, {
        headers: { Accept: "application/json" },
        cache: "no-store",
    });
    if (!response.ok) return;

    const payload = await response.json();

    const statTotal = document.getElementById("stat-total");
    const statGranted = document.getElementById("stat-granted");
    const statDenied = document.getElementById("stat-denied");
    if (statTotal) statTotal.textContent = payload.today_count;
    if (statGranted) statGranted.textContent = payload.granted_count;
    if (statDenied) statDenied.textContent = payload.denied_count;

    const body = document.getElementById("logs-body");
    if (body) {
        if (!payload.logs || payload.logs.length === 0) {
            body.innerHTML = `<tr><td colspan="4" class="logsx-empty">РќРёС‡РµРіРѕ РЅРµ РЅР°Р№РґРµРЅРѕ. РџСЂРѕРІРµСЂСЊС‚Рµ РЅРѕРјРµСЂ РёР»Рё РѕС‚РєР»СЋС‡РёС‚Рµ С„РёР»СЊС‚СЂ РїРѕ РґР°С‚Рµ.</td></tr>`;
        } else {
            body.innerHTML = payload.logs
                .map((row) => {
                    let badge = `<span class="logsx-badge">${escapeHtml(row.status)}</span>`;
                    if (row.status === "GRANTED") {
                        badge = `<span class="logsx-badge logsx-badge-good">вњ“ Р Р°Р·СЂРµС€РµРЅРѕ</span>`;
                    } else if (row.status === "DENIED") {
                        badge = `<span class="logsx-badge logsx-badge-bad">вњ• РћС‚РєР°Р·</span>`;
                    }

                    return `
                        <tr>
                            <td class="plate">${escapeHtml(row.plate)}</td>
                            <td>${badge}</td>
                            <td>${escapeHtml(row.reason || "вЂ”")}</td>
                            <td>${escapeHtml(row.created_at || "вЂ”")}</td>
                        </tr>
                    `;
                })
                .join("");
        }
    }

    const range = document.getElementById("logs-range");
    if (range) {
        const from = payload.total_count > 0 ? (payload.current_page - 1) * payload.per_page + 1 : 0;
        const to = (payload.current_page - 1) * payload.per_page + (payload.logs ? payload.logs.length : 0);
        range.textContent = `РџРѕРєР°Р·Р°РЅРѕ ${from}вЂ“${to} / ${payload.total_count}`;
    }

    const top = document.getElementById("pagination-top");
    const bottom = document.getElementById("pagination-bottom");
    if (top) renderPagination(top, payload, params);
    if (bottom) renderPagination(bottom, payload, params);

    const currentUrl = new URL(window.location.href);
    currentUrl.search = params.toString();
    window.history.replaceState({}, "", currentUrl.toString());
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("logs-filter-form");
    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const pageInput = form.querySelector('input[name="page"]');
        if (pageInput) pageInput.value = "1";
        await refreshLogs();
    });

    document.addEventListener("click", async (event) => {
        const link = event.target.closest("#pagination-top a, #pagination-bottom a");
        if (!link) return;
        event.preventDefault();
        const target = new URL(link.href, window.location.origin);
        const page = target.searchParams.get("page") || "1";
        const pageInput = form.querySelector('input[name="page"]');
        if (pageInput) pageInput.value = page;
        await refreshLogs();
    });

    setInterval(() => {
        refreshLogs().catch(() => {});
    }, 5000);
});
