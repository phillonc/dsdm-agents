import { useState, useEffect, useCallback } from 'react';
import ShoppingItem from './components/ShoppingItem';
import AddItemForm from './components/AddItemForm';
import CategoryFilter from './components/CategoryFilter';
import './App.css';

const CATEGORIES = ['Produce', 'Dairy', 'Meat', 'Bakery', 'Frozen', 'Beverages', 'Snacks', 'Household', 'Other'];

function loadItems() {
  try {
    const saved = localStorage.getItem('shoppingItems');
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
}

function saveItems(items) {
  localStorage.setItem('shoppingItems', JSON.stringify(items));
}

export default function App() {
  const [items, setItems] = useState(loadItems);
  const [filter, setFilter] = useState('All');
  const [editingId, setEditingId] = useState(null);

  useEffect(() => {
    saveItems(items);
  }, [items]);

  const addItem = useCallback((text, category, quantity) => {
    setItems(prev => [
      ...prev,
      {
        id: Date.now(),
        text,
        category,
        quantity,
        completed: false,
        createdAt: new Date().toISOString(),
      },
    ]);
  }, []);

  const toggleItem = useCallback((id) => {
    setItems(prev =>
      prev.map(item =>
        item.id === id ? { ...item, completed: !item.completed } : item
      )
    );
  }, []);

  const deleteItem = useCallback((id) => {
    setItems(prev => prev.filter(item => item.id !== id));
  }, []);

  const updateItem = useCallback((id, updates) => {
    setItems(prev =>
      prev.map(item =>
        item.id === id ? { ...item, ...updates } : item
      )
    );
    setEditingId(null);
  }, []);

  const clearCompleted = useCallback(() => {
    setItems(prev => prev.filter(item => !item.completed));
  }, []);

  const filteredItems = filter === 'All'
    ? items
    : items.filter(item => item.category === filter);

  const total = items.length;
  const completed = items.filter(i => i.completed).length;
  const remaining = total - completed;

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Shopping List</h1>
        <p className="subtitle">Keep track of everything you need</p>
      </header>

      <AddItemForm onAdd={addItem} categories={CATEGORIES} />

      <CategoryFilter
        categories={CATEGORIES}
        active={filter}
        onChange={setFilter}
        items={items}
      />

      <div className="list-section">
        {filteredItems.length === 0 ? (
          <div className="empty-message">
            {total === 0
              ? 'Your shopping list is empty. Add some items!'
              : `No items in "${filter}" category`}
          </div>
        ) : (
          <ul className="shopping-list">
            {filteredItems.map(item => (
              <ShoppingItem
                key={item.id}
                item={item}
                isEditing={editingId === item.id}
                onToggle={toggleItem}
                onDelete={deleteItem}
                onEdit={setEditingId}
                onUpdate={updateItem}
                categories={CATEGORIES}
              />
            ))}
          </ul>
        )}
      </div>

      {total > 0 && (
        <footer className="stats-bar">
          <div className="stats-info">
            <span>{total} total</span>
            <span className="stat-divider">|</span>
            <span className="stat-completed">{completed} done</span>
            <span className="stat-divider">|</span>
            <span className="stat-remaining">{remaining} remaining</span>
          </div>
          {completed > 0 && (
            <button className="clear-btn" onClick={clearCompleted}>
              Clear completed
            </button>
          )}
        </footer>
      )}
    </div>
  );
}
