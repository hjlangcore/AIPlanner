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
  Select,
  InputNumber,
  Typography
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  FileTextOutlined,
  SaveOutlined
} from '@ant-design/icons'
import { API_URL } from '../api/taskApi'

const { Title, Text } = Typography
const { Option } = Select
const { TextArea } = Input

interface KnowledgeItem {
  id: number
  title: string
  content: string
  category: string
  tags: string
  created_at: string
  updated_at: string
}

interface Category {
  name: string
}

export const KnowledgeBase: React.FC = () => {
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingItem, setEditingItem] = useState<KnowledgeItem | null>(null)
  const [form] = Form.useForm()
  const [searchKeyword, setSearchKeyword] = useState('')
  const [searchResults, setSearchResults] = useState<KnowledgeItem[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('list')

  useEffect(() => {
    fetchKnowledgeItems()
    fetchCategories()
  }, [])

  const fetchKnowledgeItems = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/knowledge`)
      const data = await response.json()
      if (data.success) {
        setKnowledgeItems(data.data)
      }
    } catch (error) {
      message.error('获取知识库失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/knowledge/categories`)
      const data = await response.json()
      if (data.success) {
        setCategories(data.categories.map((cat: string) => ({ name: cat })))
      }
    } catch (error) {
      console.error('获取分类失败', error)
    }
  }

  const handleSave = async (values: any) => {
    try {
      setSaving(true)
      const url = editingItem
        ? `${API_URL}/knowledge/${editingItem.id}`
        : `${API_URL}/knowledge`
      const method = editingItem ? 'PUT' : 'POST'
      
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })
      
      const data = await response.json()
      if (data.success) {
        message.success(editingItem ? '知识库条目更新成功' : '知识库条目添加成功')
        setModalVisible(false)
        form.resetFields()
        setEditingItem(null)
        fetchKnowledgeItems()
      } else {
        message.error(data.detail || '保存失败')
      }
    } catch (error) {
      message.error('保存知识库条目失败')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      const response = await fetch(`${API_URL}/knowledge/${id}`, {
        method: 'DELETE'
      })
      const data = await response.json()
      if (data.success) {
        message.success('知识库条目删除成功')
        fetchKnowledgeItems()
      } else {
        message.error(data.detail || '删除失败')
      }
    } catch (error) {
      message.error('删除知识库条目失败')
    }
  }

  const handleSearch = async () => {
    if (!searchKeyword.trim()) {
      message.warning('请输入搜索关键词')
      return
    }

    try {
      setSearchLoading(true)
      const response = await fetch(`${API_URL}/knowledge/search?q=${encodeURIComponent(searchKeyword)}`)
      const data = await response.json()
      if (data.success) {
        setSearchResults(data.results)
      }
    } catch (error) {
      message.error('搜索知识库失败')
    } finally {
      setSearchLoading(false)
    }
  }

  const openEditModal = (item: KnowledgeItem) => {
    setEditingItem(item)
    form.setFieldsValue({
      title: item.title,
      content: item.content,
      category: item.category,
      tags: item.tags
    })
    setModalVisible(true)
  }

  const openAddModal = () => {
    setEditingItem(null)
    form.resetFields()
    setModalVisible(true)
  }

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (text: string) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string) => (
        <Space wrap>
          {tags.split(',').map((tag, index) => (
            <Tag key={index} color="green">{tag.trim()}</Tag>
          ))}
        </Space>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: KnowledgeItem) => (
        <Space size="small">
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此知识库条目吗？"
            onConfirm={() => handleDelete(record.id)}
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
    <div className="knowledge-base">
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'list',
              label: (
                <span>
                  <FileTextOutlined />
                  知识库列表
                </span>
              ),
              children: (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <Title level={4}>知识库管理</Title>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={openAddModal}
                    >
                      添加知识库条目
                    </Button>
                  </div>

                  <Spin spinning={loading}>
                    <Table
                      columns={columns}
                      dataSource={knowledgeItems}
                      rowKey="id"
                      pagination={{ pageSize: 10 }}
                    />
                  </Spin>
                </>
              )
            },
            {
              key: 'search',
              label: (
                <span>
                  <SearchOutlined />
                  搜索知识库
                </span>
              ),
              children: (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <Space>
                      <Input
                        placeholder="输入搜索关键词"
                        value={searchKeyword}
                        onChange={(e) => setSearchKeyword(e.target.value)}
                        style={{ width: 300 }}
                      />
                      <Button
                        type="primary"
                        icon={<SearchOutlined />}
                        onClick={handleSearch}
                        loading={searchLoading}
                      >
                        搜索
                      </Button>
                    </Space>
                  </div>

                  <Spin spinning={searchLoading}>
                    <Table
                      columns={columns}
                      dataSource={searchResults}
                      rowKey="id"
                      pagination={{ pageSize: 10 }}
                      locale={{ emptyText: '搜索结果将显示在这里' }}
                    />
                  </Spin>
                </>
              )
            }
          ]}
        />
      </Card>

      <Modal
        title={editingItem ? '编辑知识库条目' : '添加知识库条目'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false)
          setEditingItem(null)
          form.resetFields()
        }}
        footer={null}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            category: '默认',
            tags: ''
          }}
        >
          <Form.Item
            label="标题"
            name="title"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input placeholder="请输入知识库条目标题" />
          </Form.Item>

          <Form.Item
            label="内容"
            name="content"
            rules={[{ required: true, message: '请输入内容' }]}
          >
            <TextArea
              placeholder="请输入知识库条目内容"
              rows={8}
              style={{ resize: 'vertical' }}
            />
          </Form.Item>

          <Form.Item label="分类" name="category">
            <Select>
              {categories.map((cat) => (
                <Option key={cat.name} value={cat.name}>{cat.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="标签" name="tags">
            <Input placeholder="多个标签用逗号分隔" />
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button
                onClick={() => {
                  setModalVisible(false)
                  setEditingItem(null)
                  form.resetFields()
                }}
              >
                取消
              </Button>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                htmlType="submit"
                loading={saving}
              >
                {editingItem ? '保存修改' : '添加条目'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default KnowledgeBase