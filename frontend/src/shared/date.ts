/** 展示接口中的 UTC 时间，转换为用户设备所在时区。 */
export function formatMatchDate(value?: string) {
  if (!value) return '时间待定'
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : value.replace(' ', 'T') + 'Z'
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return '时间待定'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date)
}
export const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
