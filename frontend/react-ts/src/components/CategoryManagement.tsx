import React, { useEffect, useState } from 'react'
import { Card, Button, Modal, Form, Input, Typography, message, Popconfirm, Tag, Row, Col } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { taskApi } from '../api/taskApi'
import { Category } from '../types/task'

const { Title, Text } = Typography

const CategoryManagement: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchCategories()
  }, [])

  const fetchCategories = async () => {
    setLoading(true)
    try {
      const res = await taskApi.getCategories()
      setCategories(res.data)
    } catch (error) {
      console.error('获取分类失败:', error)
      message.error('获取分类失败')
    } finally {
      setLoading(false)
    }
  }

  const handleOpenModal = (category?: Category) => {
    if (category) {
      setEditingCategory(category)
      form.setFieldsValue(category)
    } else {
      setEditingCategory(null)
      form.resetFields()
    }
    setModalOpen(true)
  }

  const handleCloseModal = () => {
    setModalOpen(false)
    setEditingCategory(null)
    form.resetFields()
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingCategory) {
        await taskApi.updateCategory(editingCategory.id, values)
        message.success('分类更新成功')
      } else {
        await taskApi.createCategory(values)
        message.success('分类创建成功')
      }
      handleCloseModal()
      fetchCategories()
    } catch (error) {
      console.error('保存分类失败:', error)
      message.error('保存分类失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await taskApi.deleteCategory(id)
      message.success('分类删除成功')
      fetchCategories()
    } catch (error) {
      console.error('删除分类失败:', error)
      message.error('删除分类失败')
    }
  }

  return (
    <div className="page-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>分类管理</Title>
          <Text type="secondary">管理任务分类，更好地组织任务</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
          添加分类
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        {categories.map((category) => (
          <Col xs={24} sm={12} md={8} lg={6} key={category.id}>
            <Card
              hoverable
              style={{ textAlign: 'center' }}
              actions={[
                <Button 
                  type="text" 
                  icon={<EditOutlined />} 
                  onClick={() => handleOpenModal(category)}
                >
                  编辑
                </Button>,
                <Popconfirm
                  title="确定删除此分类？"
                  description="删除后，属于该分类的任务将变为未分类"
                  onConfirm={() => handleDelete(category.id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button type="text" danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>
              ]}
            >
              <div style={{ fontSize: 32, marginBottom: 8 }}>{category.icon}</div>
              <Tag color={category.color} style={{ fontSize: 16, padding: '4px 12px' }}>
                {category.name}
              </Tag>
            </Card>
          </Col>
        ))}
      </Row>

      {categories.length === 0 && !loading && (
        <div className="empty-state">暂无分类，点击"添加分类"开始创建</div>
      )}

      <Modal
        title={editingCategory ? '编辑分类' : '添加分类'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={handleCloseModal}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="分类名称"
            rules={[{ required: true, message: '请输入分类名称' }]}
          >
            <Input placeholder="例如：工作、学习、生活" />
          </Form.Item>

          <Form.Item name="icon" label="图标 (Emoji)">
            <Input placeholder="例如：📁 💼 📚 🏠" />
          </Form.Item>

          <Form.Item name="color" label="颜色">
            <Input placeholder="例如：#3b82f6" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default CategoryManagement
