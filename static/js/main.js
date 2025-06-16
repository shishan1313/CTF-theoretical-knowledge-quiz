document.addEventListener("DOMContentLoaded", () => {
  // 添加活动导航链接高亮
  highlightActiveNavLink()

  // 初始化表单验证
  initFormValidation()

  // 初始化闪现消息自动消失
  initFlashMessages()

  // 初始化考试倒计时（如果在考试页面）
  if (document.querySelector(".exam-timer")) {
    initExamTimer()
  }

  // 初始化选项选择效果
  initOptionSelection()
})

// 高亮当前页面的导航链接
function highlightActiveNavLink() {
  const currentPath = window.location.pathname
  const navLinks = document.querySelectorAll(".nav-link")

  navLinks.forEach((link) => {
    const href = link.getAttribute("href")
    if (href === currentPath || (href !== "/" && currentPath.startsWith(href))) {
      link.classList.add("active")
    }
  })
}

// 表单验证
function initFormValidation() {
  const forms = document.querySelectorAll("form")

  forms.forEach((form) => {
    form.addEventListener("submit", (event) => {
      const requiredFields = form.querySelectorAll("[required]")
      let isValid = true

      requiredFields.forEach((field) => {
        if (!field.value.trim()) {
          isValid = false
          field.classList.add("is-invalid")

          // 如果还没有错误提示，添加一个
          if (!field.nextElementSibling || !field.nextElementSibling.classList.contains("error-message")) {
            const errorMsg = document.createElement("div")
            errorMsg.className = "error-message"
            errorMsg.textContent = "此字段不能为空"
            errorMsg.style.color = "var(--danger-color)"
            errorMsg.style.fontSize = "14px"
            errorMsg.style.marginTop = "5px"
            field.parentNode.insertBefore(errorMsg, field.nextSibling)
          }
        } else {
          field.classList.remove("is-invalid")

          // 移除错误提示
          if (field.nextElementSibling && field.nextElementSibling.classList.contains("error-message")) {
            field.nextElementSibling.remove()
          }
        }
      })

      if (!isValid) {
        event.preventDefault()
      }
    })

    // 输入时移除错误状态
    const inputs = form.querySelectorAll("input, select, textarea")
    inputs.forEach((input) => {
      input.addEventListener("input", function () {
        this.classList.remove("is-invalid")
        if (this.nextElementSibling && this.nextElementSibling.classList.contains("error-message")) {
          this.nextElementSibling.remove()
        }
      })
    })
  })
}

// 闪现消息自动消失
function initFlashMessages() {
  const flashMessages = document.querySelectorAll(".flash")

  flashMessages.forEach((message) => {
    setTimeout(() => {
      message.style.opacity = "0"
      message.style.transform = "translateY(-10px)"
      message.style.transition = "opacity 0.5s, transform 0.5s"

      setTimeout(() => {
        message.remove()
      }, 500)
    }, 5000)
  })
}

// 考试倒计时
function initExamTimer() {
  const timerElement = document.querySelector(".exam-timer")
  const endTimeStr = timerElement.getAttribute("data-end-time")

  if (!endTimeStr) return

  const endTime = new Date(endTimeStr).getTime()

  const timer = setInterval(() => {
    const now = new Date().getTime()
    const distance = endTime - now

    if (distance < 0) {
      clearInterval(timer)
      timerElement.innerHTML = "考试已结束"
      document.querySelector("form").submit()
      return
    }

    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60))
    const seconds = Math.floor((distance % (1000 * 60)) / 1000)

    timerElement.innerHTML = `剩余时间: ${hours}时 ${minutes}分 ${seconds}秒`
  }, 1000)
}

// 选项选择效果
function initOptionSelection() {
  const optionLabels = document.querySelectorAll(".option-label")

  optionLabels.forEach((label) => {
    label.addEventListener("click", function () {
      // 找到同一问题下的所有选项
      const questionCard = this.closest(".question-card")
      const allOptions = questionCard.querySelectorAll(".option-label")

      // 移除所有选中状态
      allOptions.forEach((opt) => {
        opt.classList.remove("selected")
      })

      // 添加当前选中状态
      this.classList.add("selected")
    })
  })
}

// 确认删除
function confirmDelete(message) {
  return confirm(message || "确定要删除吗？")
}
