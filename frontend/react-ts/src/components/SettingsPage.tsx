import React, { useState, useEffect } from 'react'
import {
  Card,
  Tabs,
  Form,
  Input,
  Button,
  Space,
  Table,
  Tag,
  Modal,
  message,
  Popconfirm,
  Spin,
  Alert,
  Descriptions,
  Typography,
  Divider,
  InputNumber,
  Radio,
  Select
} from 'antd'
import {
  MailOutlined,
  SaveOutlined,
  SendOutlined,
  DeleteOutlined,
  DownloadOutlined,
  UploadOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  PlusOutlined,
  TagOutlined,
  GlobalOutlined
} from '@ant-design/icons'
import { API_URL } from '../api/taskApi'
import { useAuthStore } from '../store/authStore'
import { useI18n, Language } from '../i18n'

const { Title, Text } = Typography

interface EmailConfig {
  smtp_host: string
  smtp_port: number
  smtp_user: string
  sender_email: string
  receiver_email: string
  is_configured: boolean
}

interface BackupInfo {
  filename: string
  path: string
  size: number
  created_at: string
  modified_at: string
}

interface TagInfo {
  id: number
  name: string
  color: string
  usage_count: number
}

export const SettingsPage: React.FC = () => {
  const [emailForm] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [emailConfig, setEmailConfig] = useState<EmailConfig | null>(null)
  const [backups, setBackups] = useState<BackupInfo[]>([])
  const [backupsLoading, setBackupsLoading] = useState(false)
  const [backupInfo, setBackupInfo] = useState<any>(null)
  const [selectedBackup, setSelectedBackup] = useState<string | null>(null)
  const [restoreModalVisible, setRestoreModalVisible] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [tags, setTags] = useState<TagInfo[]>([])
  const [tagsLoading, setTagsLoading] = useState(false)
  const [tagModalVisible, setTagModalVisible] = useState(false)
  const [editingTag, setEditingTag] = useState<TagInfo | null>(null)
  const [tagForm] = Form.useForm()

  const { } = useAuthStore()
  const { language, setLanguage, t } = useI18n()

  const handleLanguageChange = (lang: Language) => {
    setLanguage(lang)
    message.success(lang === 'zh-CN' ? '语言设置已更新为中文' : 'Language settings updated to English')
  }

  useEffect(() => {
    fetchEmailConfig()
    fetchBackups()
    fetchTags()
  }, [])

  const fetchEmailConfig = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/email/config`)
      const data = await response.json()
      if (data.success && data.config) {
        setEmailConfig(data.config)
        emailForm.setFieldsValue({
          smtp_host: data.config.smtp_host,
          smtp_port: data.config.smtp_port,
          smtp_user: data.config.smtp_user,
          sender_email: data.config.sender_email,
          receiver_email: data.config.receiver_email
        })
      }
    } catch (error) {
      message.error('获取邮件配置失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchBackups = async () => {
    try {
      setBackupsLoading(true)
      const response = await fetch(`${API_URL}/backup/list`)
      const data = await response.json()
      if (data.success) {
        setBackups(data.backups)
      }
    } catch (error) {
      message.error('获取备份列表失败')
    } finally {
      setBackupsLoading(false)
    }
  }

  const handleSaveEmailConfig = async (values: any) => {
    try {
      setSaving(true)
      const response = await fetch(`${API_URL}/email/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })
      const data = await response.json()
      if (data.success) {
        message.success('邮件配置保存成功')
        fetchEmailConfig()
      } else {
        message.error(data.detail || '保存失败')
      }
    } catch (error) {
      message.error('保存邮件配置失败')
    } finally {
      setSaving(false)
    }
  }

  const handleTestEmail = async () => {
    try {
      setTesting(true)
      const response = await fetch(`${API_URL}/email/test`, {
        method: 'POST'
      })
      const data = await response.json()
      if (data.success) {
        message.success('测试邮件发送成功，请检查收件箱')
      } else {
        message.error(data.message || '测试邮件发送失败')
      }
    } catch (error) {
      message.error('发送测试邮件失败')
    } finally {
      setTesting(false)
    }
  }

  const handleCreateBackup = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/backup/create?backup_type=manual`, {
        method: 'POST'
      })
      const data = await response.json()
      if (data.success) {
        message.success('备份创建成功')
        fetchBackups()
      } else {
        message.error(data.detail || '备份创建失败')
      }
    } catch (error) {
      message.error('创建备份失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRestoreBackup = async (clearExisting: boolean) => {
    if (!selectedBackup) return

    try {
      setRestoring(true)
      const response = await fetch(`${API_URL}/backup/restore/${selectedBackup}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clear_existing: clearExisting })
      })
      const data = await response.json()
      if (data.success) {
        message.success('数据恢复成功')
        setRestoreModalVisible(false)
      } else {
        message.error(data.detail || '恢复失败')
      }
    } catch (error) {
      message.error('恢复备份失败')
    } finally {
      setRestoring(false)
    }
  }

  const handleDeleteBackup = async (filename: string) => {
    try {
      const response = await fetch(`${API_URL}/backup/${filename}`, {
        method: 'DELETE'
      })
      const data = await response.json()
      if (data.success) {
        message.success('备份已删除')
        fetchBackups()
      } else {
        message.error(data.detail || '删除失败')
      }
    } catch (error) {
      message.error('删除备份失败')
    }
  }

  const handleExportJson = async () => {
    try {
      const response = await fetch(`${API_URL}/export/json`)
      const data = await response.json()
      if (data.success) {
        const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `smart_planner_export_${new Date().toISOString().slice(0, 10)}.json`
        a.click()
        URL.revokeObjectURL(url)
        message.success('JSON导出成功')
      }
    } catch (error) {
      message.error('导出失败')
    }
  }

  const handleExportCsv = async () => {
    try {
      const response = await fetch(`${API_URL}/export/csv`)
      const data = await response.json()
      if (data.success) {
        message.success('CSV导出成功，文件已保存到: ' + data.csv_path)
      }
    } catch (error) {
      message.error('导出失败')
    }
  }

  const showBackupInfo = async (filename: string) => {
    try {
      const response = await fetch(`${API_URL}/backup/info/${filename}`)
      const data = await response.json()
      if (data.success) {
        setBackupInfo(data.info)
        setSelectedBackup(filename)
      }
    } catch (error) {
      message.error('获取备份信息失败')
    }
  }

  const fetchTags = async () => {
    try {
      setTagsLoading(true)
      const response = await fetch(`${API_URL}/tags`)
      const data = await response.json()
      if (data.success) {
        setTags(data.tags)
      }
    } catch (error) {
      message.error('获取标签列表失败')
    } finally {
      setTagsLoading(false)
    }
  }

  const handleCreateTag = async (values: any) => {
    try {
      const response = await fetch(`${API_URL}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })
      const data = await response.json()
      if (data.success) {
        message.success('标签创建成功')
        setTagModalVisible(false)
        tagForm.resetFields()
        fetchTags()
      } else {
        message.error(data.detail || '创建失败')
      }
    } catch (error) {
      message.error('创建标签失败')
    }
  }

  const handleUpdateTag = async (values: any) => {
    if (!editingTag) return
    try {
      const response = await fetch(`${API_URL}/tags/${editingTag.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })
      const data = await response.json()
      if (data.success) {
        message.success('标签更新成功')
        setTagModalVisible(false)
        setEditingTag(null)
        tagForm.resetFields()
        fetchTags()
      } else {
        message.error(data.detail || '更新失败')
      }
    } catch (error) {
      message.error('更新标签失败')
    }
  }

  const handleDeleteTag = async (tagId: number) => {
    try {
      const response = await fetch(`${API_URL}/tags/${tagId}`, {
        method: 'DELETE'
      })
      const data = await response.json()
      if (data.success) {
        message.success('标签删除成功')
        fetchTags()
      } else {
        message.error(data.detail || '删除失败')
      }
    } catch (error) {
      message.error('删除标签失败')
    }
  }

  const openEditTagModal = (tag: TagInfo) => {
    setEditingTag(tag)
    tagForm.setFieldsValue({ name: tag.name, color: tag.color })
    setTagModalVisible(true)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  }

  const backupColumns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (text: string) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => formatFileSize(size)
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => formatDate(date)
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: BackupInfo) => (
        <Space size="small">
          <Button size="small" onClick={() => showBackupInfo(record.filename)}>
            详情
          </Button>
          <Popconfirm
            title="确定要删除此备份吗？"
            onConfirm={() => handleDeleteBackup(record.filename)}
            okText="确定"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div className="settings-page">
      <Card>
        <Tabs 
          defaultActiveKey="email" 
          tabPosition="top"
          items={[
            {
              key: 'language',
              label: (
                <span>
                  <GlobalOutlined />
                  语言设置
                </span>
              ),
              children: (
                <Card title="界面语言设置">
                  <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <div>
                      <Title level={5}>选择显示语言</Title>
                      <Text type="secondary">
                        选择您偏好的界面语言，设置会自动保存。
                      </Text>
                      <div style={{ marginTop: 16 }}>
                        <Select
                          style={{ width: 200 }}
                          value={language}
                          onChange={handleLanguageChange}
                          options={[
                            { value: 'zh-CN', label: '中文 (简体)' },
                            { value: 'en-US', label: 'English' }
                          ]}
                        />
                      </div>
                    </div>

                    <Divider />

                    <div>
                      <Alert
                        type="info"
                        message="语言切换说明"
                        description="语言切换后，界面文字会立即更新。部分内容（如您创建的任务和数据）可能无法翻译，因为它们是您个人输入的内容。"
                        showIcon
                      />
                    </div>
                  </Space>
                </Card>
              )
            },
            {
              key: 'email',
              label: (
                <span>
                  <MailOutlined />
                  邮件配置
                </span>
              ),
              children: (
                <>
                  <Card title="SMTP邮件服务器配置" style={{ marginBottom: 16 }}>
                    <Form
                      form={emailForm}
                      layout="vertical"
                      onFinish={handleSaveEmailConfig}
                      initialValues={{
                        smtp_port: 587
                      }}
                    >
                      <Form.Item
                        label="SMTP服务器地址"
                        name="smtp_host"
                        rules={[{ required: true, message: '请输入SMTP服务器地址' }]}
                      >
                        <Input placeholder="smtp.example.com" />
                      </Form.Item>

                      <Form.Item
                        label="SMTP端口"
                        name="smtp_port"
                        rules={[{ required: true, message: '请输入SMTP端口' }]}
                      >
                        <InputNumber min={1} max={65535} style={{ width: 200 }} />
                      </Form.Item>

                      <Form.Item
                        label="SMTP用户名"
                        name="smtp_user"
                        rules={[{ required: true, message: '请输入SMTP用户名' }]}
                      >
                        <Input placeholder="your@email.com" />
                      </Form.Item>

                      <Form.Item
                        label="SMTP密码"
                        name="smtp_password"
                        tooltip="如果不修改密码，请留空"
                      >
                        <Input.Password placeholder="输入新密码以更新" />
                      </Form.Item>

                      <Form.Item label="发件人邮箱" name="sender_email">
                        <Input placeholder="与用户名相同或自定义" />
                      </Form.Item>

                      <Form.Item
                        label="收件人邮箱"
                        name="receiver_email"
                        rules={[
                          { required: true, message: '请输入收件人邮箱' },
                          { type: 'email', message: '请输入有效的邮箱地址' }
                        ]}
                      >
                        <Input placeholder="receive@email.com" />
                      </Form.Item>

                      <Form.Item>
                        <Space>
                          <Button
                            type="primary"
                            htmlType="submit"
                            icon={<SaveOutlined />}
                            loading={saving}
                          >
                            保存配置
                          </Button>
                          <Button
                            icon={<SendOutlined />}
                            onClick={handleTestEmail}
                            loading={testing}
                            disabled={!emailConfig?.is_configured}
                          >
                            发送测试邮件
                          </Button>
                        </Space>
                      </Form.Item>
                    </Form>

                    {!emailConfig?.is_configured && (
                      <Alert
                        type="warning"
                        message="邮件服务未配置"
                        description="请填写上方表单配置SMTP服务器信息，配置完成后可以发送测试邮件验证。"
                        showIcon
                        style={{ marginTop: 16 }}
                      />
                    )}

                    {emailConfig?.is_configured && (
                      <Alert
                        type="success"
                        message="邮件服务已配置"
                        description="配置已完成，可以发送测试邮件验证是否正常工作。"
                        showIcon
                        icon={<CheckCircleOutlined />}
                        style={{ marginTop: 16 }}
                      />
                    )}
                  </Card>

                  <Card title="邮件提醒说明">
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label="SMTP端口">
                        通常为 587 (TLS) 或 465 (SSL)
                      </Descriptions.Item>
                      <Descriptions.Item label="Gmail配置">
                        SMTP服务器: smtp.gmail.com，端口: 587，需要开启"低安全性应用访问"
                      </Descriptions.Item>
                      <Descriptions.Item label="QQ邮箱配置">
                        SMTP服务器: smtp.qq.com，端口: 587，需要在设置中开启SMTP服务
                      </Descriptions.Item>
                      <Descriptions.Item label="163邮箱配置">
                        SMTP服务器: smtp.163.com，端口: 465，需要在设置中开启SMTP服务
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                </>
              )
            },
            {
              key: 'backup',
              label: (
                <span>
                  <CloudUploadOutlined />
                  数据备份
                </span>
              ),
              children: (
                <>
                  <Card title="数据备份与恢复">
                    <Space direction="vertical" style={{ width: '100%' }} size="large">
                      <div>
                        <Title level={5}>创建备份</Title>
                        <Text type="secondary">
                          创建数据库的完整备份，包含所有任务、分类、知识和聊天记录。
                        </Text>
                        <div style={{ marginTop: 16 }}>
                          <Space>
                            <Button
                              type="primary"
                              icon={<CloudUploadOutlined />}
                              onClick={handleCreateBackup}
                              loading={loading}
                            >
                              创建备份
                            </Button>
                            <Button icon={<DownloadOutlined />} onClick={handleExportJson}>
                              导出JSON
                            </Button>
                            <Button icon={<UploadOutlined />} onClick={handleExportCsv}>
                              导出CSV
                            </Button>
                          </Space>
                        </div>
                      </div>

                      <Divider />

                      <div>
                        <Title level={5}>备份历史</Title>
                        <Spin spinning={backupsLoading}>
                          <Table
                            columns={backupColumns}
                            dataSource={backups}
                            rowKey="filename"
                            pagination={{ pageSize: 5 }}
                            size="small"
                          />
                        </Spin>
                      </div>
                    </Space>
                  </Card>

                  {backupInfo && (
                    <Card title="备份详情" style={{ marginTop: 16 }}>
                      <Descriptions column={2}>
                        <Descriptions.Item label="文件名">{backupInfo.filename}</Descriptions.Item>
                        <Descriptions.Item label="大小">
                          {formatFileSize(backupInfo.size)}
                        </Descriptions.Item>
                        <Descriptions.Item label="创建时间">
                          {formatDate(backupInfo.created_at)}
                        </Descriptions.Item>
                        <Descriptions.Item label="导出时间">
                          {backupInfo.export_time || '-'}
                        </Descriptions.Item>
                        <Descriptions.Item label="版本">{backupInfo.version}</Descriptions.Item>
                      </Descriptions>

                      {backupInfo.data_info && (
                        <>
                          <Divider>数据统计</Divider>
                          <Descriptions column={3}>
                            <Descriptions.Item label="任务数">
                              {backupInfo.data_info.tasks_count}
                            </Descriptions.Item>
                            <Descriptions.Item label="分类数">
                              {backupInfo.data_info.categories_count}
                            </Descriptions.Item>
                            <Descriptions.Item label="知识库条目">
                              {backupInfo.data_info.knowledge_count}
                            </Descriptions.Item>
                            <Descriptions.Item label="对话会话">
                              {backupInfo.data_info.chat_sessions_count}
                            </Descriptions.Item>
                            <Descriptions.Item label="聊天记录">
                              {backupInfo.data_info.chat_messages_count}
                            </Descriptions.Item>
                          </Descriptions>
                        </>
                      )}

                      <div style={{ marginTop: 16 }}>
                        <Space>
                          <Button
                            type="primary"
                            onClick={() => {
                              setSelectedBackup(backupInfo.filename)
                              setRestoreModalVisible(true)
                            }}
                          >
                            恢复此备份
                          </Button>
                        </Space>
                      </div>
                    </Card>
                  )}
                </>
              )
            },
            {
              key: 'tags',
              label: (
                <span>
                  <TagOutlined />
                  标签管理
                </span>
              ),
              children: (
                <Card title="任务标签管理">
                  <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <div>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => {
                          setEditingTag(null)
                          tagForm.resetFields()
                          setTagModalVisible(true)
                        }}
                      >
                        创建标签
                      </Button>
                    </div>

                    <Spin spinning={tagsLoading}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {tags.map((tag) => (
                          <Tag
                            key={tag.id}
                            color={tag.color}
                            style={{ padding: '4px 12px', fontSize: '14px', cursor: 'pointer' }}
                            onClick={() => openEditTagModal(tag)}
                            closable
                            onClose={(e) => {
                              e.stopPropagation()
                              handleDeleteTag(tag.id)
                            }}
                          >
                            {tag.name} ({tag.usage_count})
                          </Tag>
                        ))}
                      </div>
                    </Spin>

                    <Alert
                      type="info"
                      message="标签使用提示"
                      description="点击标签可编辑，关闭按钮可删除标签。标签的使用次数会在关联任务时自动更新。"
                      showIcon
                    />
                  </Space>
                </Card>
              )
            }
          ]}
        />
      </Card>

      <Modal
        title="恢复备份"
        open={restoreModalVisible}
        onCancel={() => setRestoreModalVisible(false)}
        footer={null}
      >
        <div style={{ padding: '16px 0' }}>
          <Text>确定要从以下备份恢复数据吗？</Text>
          <br />
          <Tag color="blue" style={{ marginTop: 8 }}>
            {selectedBackup}
          </Tag>

          <Alert
            type="warning"
            message="请选择恢复模式"
            description={
              <Radio.Group
                onChange={() => {}}
                id="restore_mode"
              >
                <Space direction="vertical">
                  <Radio value={false}>
                    <Text>合并模式（推荐）</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      在现有数据基础上添加备份数据，不会删除现有数据
                    </Text>
                  </Radio>
                  <Radio value={true}>
                    <Text>覆盖模式</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      清空现有数据后导入备份数据，会丢失未包含在备份中的数据
                    </Text>
                  </Radio>
                </Space>
              </Radio.Group>
            }
            style={{ marginTop: 16 }}
          />
        </div>

        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
          <Button onClick={() => setRestoreModalVisible(false)}>取消</Button>
          <Button
            type="primary"
            danger
            loading={restoring}
            onClick={() => {
              const mode = (document.getElementById('restore_mode') as any)?.value === true
              handleRestoreBackup(mode)
            }}
          >
            确定恢复
          </Button>
        </Space>
      </Modal>

      <Modal
        title={editingTag ? '编辑标签' : '创建标签'}
        open={tagModalVisible}
        onCancel={() => {
          setTagModalVisible(false)
          setEditingTag(null)
          tagForm.resetFields()
        }}
        footer={null}
      >
        <Form
          form={tagForm}
          layout="vertical"
          onFinish={editingTag ? handleUpdateTag : handleCreateTag}
          initialValues={{ color: '#5b7cff' }}
        >
          <Form.Item
            label="标签名称"
            name="name"
            rules={[{ required: true, message: '请输入标签名称' }]}
          >
            <Input placeholder="请输入标签名称" />
          </Form.Item>

          <Form.Item
            label="标签颜色"
            name="color"
            rules={[{ required: true, message: '请选择颜色' }]}
          >
            <Input type="color" style={{ width: '100%', height: '40px' }} />
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => {
                setTagModalVisible(false)
                setEditingTag(null)
                tagForm.resetFields()
              }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingTag ? '保存' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default SettingsPage
