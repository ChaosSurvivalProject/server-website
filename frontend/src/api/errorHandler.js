/**
 * 错误处理工具
 * 提供统一的错误提示功能
 */

/**
 * 显示错误提示弹窗
 * @param {string} message - 错误信息
 * @param {string} title - 弹窗标题，默认'错误提示'
 */
export function showError(message, title = '错误提示') {
  // 创建弹窗容器
  const errorModal = document.createElement('div');
  errorModal.className = 'error-modal';
  errorModal.style.cssText = `
    position: fixed;
    z-index: 2000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: ui-monospace, 'Cascadia Mono', Consolas, Menlo, 'Microsoft YaHei', monospace;
  `;
  
  // 创建弹窗内容
  const modalContent = document.createElement('div');
  modalContent.className = 'error-modal-content';
  modalContent.style.cssText = `
    background-color: white;
    padding: 20px;
    border: 4px solid #7CB342;
    box-shadow: 4px 4px 0 0 #43A047;
    width: 90%;
    max-width: 400px;
    text-align: center;
    position: relative;
  `;
  
  // 创建标题
  const modalTitle = document.createElement('h3');
  modalTitle.textContent = title;
  modalTitle.style.cssText = `
    color: #C62828;
    margin-top: 0;
    margin-bottom: 15px;
    font-size: 18px;
  `;
  
  // 创建错误消息
  const errorMessage = document.createElement('p');
  errorMessage.textContent = message;
  errorMessage.style.cssText = `
    margin-bottom: 20px;
    line-height: 1.6;
    color: #424242;
  `;
  
  // 创建关闭按钮
  const closeButton = document.createElement('button');
  closeButton.textContent = '确定';
  closeButton.style.cssText = `
    background-color: #7CB342;
    color: white;
    border: 2px solid #43A047;
    padding: 8px 20px;
    cursor: pointer;
    font-family: inherit;
    font-size: 14px;
    transition: background-color 0.3s;
  `;
  
  // 关闭按钮事件
  closeButton.onclick = () => {
    document.body.removeChild(errorModal);
  };
  
  // 点击弹窗外部关闭
  errorModal.onclick = (e) => {
    if (e.target === errorModal) {
      document.body.removeChild(errorModal);
    }
  };
  
  // 组装弹窗
  modalContent.appendChild(modalTitle);
  modalContent.appendChild(errorMessage);
  modalContent.appendChild(closeButton);
  errorModal.appendChild(modalContent);
  
  // 添加到页面
  document.body.appendChild(errorModal);
}

/**
 * 处理API错误响应
 * @param {Object} response - API响应对象
 * @returns {Object} - 处理后的响应数据
 */
export function handleAPIError(response) {
  // 根据响应对象格式处理错误
  if (response.code !== undefined) {
    if (response.code === 0 || response.code === 200) {
      // 成功响应
      return response.data || response;
    } else {
      // 失败响应，显示错误信息
      const errorMessage = response.message || `请求失败，错误码: ${response.code}`;
      showError(errorMessage);
      throw new Error(errorMessage);
    }
  }
  
  // 未定义code的情况，可能是其他格式的响应
  return response;
}

// 导出错务处理工具
export default {
  showError,
  handleAPIError
};