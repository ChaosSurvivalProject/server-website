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