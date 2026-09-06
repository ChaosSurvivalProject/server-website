/**
 * 将 ISO 时间字符串中的 "T" 分隔符替换为空格，用于公告等页面展示。
 * 例：'2026-09-06T11:47:00' -> '2026-09-06 11:47:00'
 */
export function formatDateTime(timeStr) {
    if (!timeStr) return "";
    return String(timeStr).replace("T", " ");
}

export function formatHour(timeStr) {
    // 将时间字符串格式化为小时显示
    if (!timeStr) return '00:00';
    // 假设时间格式为 'YYYY-MM-DD HH:MM:SS'
    const parts = timeStr.split(' ');
    if (parts.length > 1) {
        const timePart = parts[1];
        // 只返回小时部分
        return timePart.split(':').slice(0, 2).join(':');
    }
    return '00:00';
}