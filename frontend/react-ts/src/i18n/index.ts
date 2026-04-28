import React, { createContext, useContext, useState, useEffect } from 'react'

export type Language = 'zh-CN' | 'en-US'

type TranslateFn = (key: string, params?: Record<string, any>) => string

interface Locale {
  [key: string]: string | Locale
}

const zhCN: Locale = {
  common: {
    save: '保存',
    cancel: '取消',
    confirm: '确定',
    delete: '删除',
    edit: '编辑',
    add: '添加',
    search: '搜索',
    loading: '加载中...',
    success: '成功',
    error: '错误',
    warning: '警告',
    info: '信息'
  }
}

const enUS: Locale = {
  common: {
    save: 'Save',
    cancel: 'Cancel',
    confirm: 'Confirm',
    delete: 'Delete',
    edit: 'Edit',
    add: 'Add',
    search: 'Search',
    loading: 'Loading...',
    success: 'Success',
    error: 'Error',
    warning: 'Warning',
    info: 'Info'
  }
}

const locales: Record<Language, Locale> = {
  'zh-CN': zhCN,
  'en-US': enUS
}

const translate = (lang: Language, key: string, params?: Record<string, any>): string => {
  const keys = key.split('.')
  let value: any = locales[lang]
  
  for (const k of keys) {
    if (value && typeof value === 'object' && k in value) {
      value = value[k]
    } else {
      return key
    }
  }
  
  if (typeof value === 'string' && params) {
    return value.replace(/\{(\w+)\}/g, (_, paramName) => {
      return params[paramName] !== undefined ? String(params[paramName]) : `{${paramName}}`
    })
  }
  
  return typeof value === 'string' ? value : key
}

interface I18nContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: TranslateFn
}

const I18nContext = createContext<I18nContextType | undefined>(undefined)

interface I18nProviderProps {
  children: React.ReactNode
}

export const I18nProvider: React.FC<I18nProviderProps> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>('zh-CN')
  
  useEffect(() => {
    const savedLang = localStorage.getItem('language') as Language
    if (savedLang && (savedLang === 'zh-CN' || savedLang === 'en-US')) {
      setLanguageState(savedLang)
    }
  }, [])
  
  const setLanguage = (lang: Language) => {
    setLanguageState(lang)
    localStorage.setItem('language', lang)
  }
  
  const t: TranslateFn = (key: string, params?: Record<string, any>) => {
    return translate(language, key, params)
  }
  
  const providerValue = {
    language: language,
    setLanguage: setLanguage,
    t: t
  }
  
  return React.createElement(
    I18nContext.Provider,
    { value: providerValue },
    children
  )
}

export const useI18n = () => {
  const context = useContext(I18nContext)
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider')
  }
  return context
}

export default I18nProvider