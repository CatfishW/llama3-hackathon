import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth/AuthContext'

type Friend = {
  id: number
  requester_id: number
  requested_id: number
  status: 'PENDING' | 'ACCEPTED' | 'BLOCKED'
  created_at: string
  requester: {
    id: number
    email: string
    full_name?: string
    profile_picture?: string
    level: number
    is_online: boolean
  }
  requested: {
    id: number
    email: string
    full_name?: string
    profile_picture?: string
    level: number
    is_online: boolean
  }
}

type UserSearch = {
  id: number
  email: string
  display_name?: string
  profile_picture?: string
  school?: string
  is_friend: boolean
  has_pending_request: boolean
}

export default function Friends() {
  const { user } = useAuth()
  const [friends, setFriends] = useState<Friend[]>([])
  const [searchResults, setSearchResults] = useState<UserSearch[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<'friends' | 'search' | 'requests'>('friends')
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [showAlert, setShowAlert] = useState<{ type: 'success' | 'error' | 'warning', message: string } | null>(null)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    loadFriends()
  }, [])

  useEffect(()=>{ 
    const upd=()=>setIsMobile(window.innerWidth<780); 
    upd(); 
    window.addEventListener('resize',upd); 
    window.addEventListener('orientationchange',upd); 
    return ()=>{
      window.removeEventListener('resize',upd); 
      window.removeEventListener('orientationchange',upd)
    } 
  }, [])

  async function loadFriends() {
    try {
      setLoading(true)
      const res = await api.get('/api/friends')
      setFriends(res.data)
    } catch (e) {
      console.error('Failed to load friends', e)
    } finally {
      setLoading(false)
    }
  }

  async function searchUsers() {
    if (!searchQuery.trim()) return
    
    try {
      setSearching(true)
      const res = await api.get(`/api/users/search?q=${encodeURIComponent(searchQuery)}`)
      setSearchResults(res.data)
      setActiveTab('search')
    } catch (e) {
      console.error('Failed to search users', e)
    } finally {
      setSearching(false)
    }
  }

  async function sendFriendRequest(userId: number) {
    try {
      await api.post(`/api/friends/request`, { requested_id: userId })
      setSearchResults(prev => 
        prev.map(user => 
          user.id === userId 
            ? { ...user, has_pending_request: true }
            : user
        )
      )
      setShowAlert({ type: 'success', message: 'Friend request sent successfully!' })
    } catch (e: any) {
      console.error('Failed to send friend request', e)
      const message = e.response?.data?.detail || 'Failed to send friend request'
      setShowAlert({ type: 'error', message })
    }
  }

  async function respondToRequest(userId: number, accept: boolean) {
    try {
      await api.post(`/api/friends/respond`, { user_id: userId, accept })
      loadFriends()
      setShowAlert({ 
        type: 'success', 
        message: accept ? 'Friend request accepted!' : 'Friend request rejected!' 
      })
    } catch (e: any) {
      console.error('Failed to respond to friend request', e)
      const message = e.response?.data?.detail || 'Failed to respond to friend request'
      setShowAlert({ type: 'error', message })
    }
  }

  async function removeFriend(userId: number) {
    if (!confirm('Remove this friend?')) return
    
    try {
      await api.delete(`/api/friends/${userId}`)
      loadFriends()
    } catch (e) {
      console.error('Failed to remove friend', e)
    }
  }

  const containerStyle: React.CSSProperties = {
    maxWidth: '1000px',
    margin: '0 auto',
    padding: isMobile? '28px 14px':'40px 20px'
  }

  const tabStyle = (active: boolean) => ({
    padding: '12px 24px',
    borderRadius: '8px',
    border: 'none',
    background: active ? 'rgba(78, 205, 196, 0.3)' : 'rgba(255, 255, 255, 0.1)',
    color: 'white',
    cursor: 'pointer',
    fontWeight: '600',
    transition: 'all 0.3s ease'
  })

  const cardStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    padding: '25px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    marginBottom: '15px'
  }

  const userCardStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: isMobile? '10px':'15px',
    padding: isMobile? '16px 14px':'20px',
    background: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '10px',
    marginBottom: '15px',
    transition: 'all 0.3s ease'
  }

  const buttonStyle = (variant: 'primary' | 'secondary' | 'danger') => {
    const variants = {
      primary: 'linear-gradient(45deg, #4ecdc4, #44a08d)',
      secondary: 'rgba(255, 255, 255, 0.2)',
      danger: 'linear-gradient(45deg, #ff6b6b, #ee5a52)'
    }
    
    return {
      background: variants[variant],
      color: 'white',
      border: 'none',
      padding: '8px 16px',
      borderRadius: '6px',
      fontSize: '0.9rem',
      fontWeight: '500',
      cursor: 'pointer',
      transition: 'all 0.3s ease'
    }
  }

  // Auto-hide alert after 5 seconds
  useEffect(() => {
    if (showAlert) {
      const timer = setTimeout(() => setShowAlert(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [showAlert])

  // Filter friends and requests based on current user
  const currentUserId = user?.id
  
  // Pending requests received by current user (where they are the requested user)
  const incomingRequests = friends.filter(f => 
    f.status === 'PENDING' && 
    f.requested_id === currentUserId
  )
  
  // Pending requests sent by current user (where they are the requester)
  const outgoingRequests = friends.filter(f => 
    f.status === 'PENDING' && 
    f.requester_id === currentUserId
  )
  
  // All pending requests (for the tab counter)
  const allPendingRequests = friends.filter(f => f.status === 'PENDING')
  
  const acceptedFriends = friends.filter(f => f.status === 'ACCEPTED')

  // Helper function to get the friend user data
  function getFriendUser(friendship: Friend, currentUserId: number) {
    return friendship.requester_id === currentUserId ? friendship.requested : friendship.requester
  }

  return (
    <div style={containerStyle}>
      {/* Alert popup */}
      {showAlert && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          background: showAlert.type === 'success' ? 'linear-gradient(45deg, #4ecdc4, #44a08d)' :
                     showAlert.type === 'error' ? 'linear-gradient(45deg, #ff6b6b, #ee5a52)' :
                     'linear-gradient(45deg, #ffd93d, #ff9a56)',
          color: 'white',
          padding: '15px 20px',
          borderRadius: '10px',
          boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)',
          backdropFilter: 'blur(10px)',
          zIndex: 1000,
          maxWidth: '400px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          animation: 'slideIn 0.3s ease-out'
        }}>
          <i className={`fas ${
            showAlert.type === 'success' ? 'fa-check-circle' :
            showAlert.type === 'error' ? 'fa-exclamation-circle' :
            'fa-exclamation-triangle'
          }`}></i>
          <span>{showAlert.message}</span>
          <button
            onClick={() => setShowAlert(null)}
            style={{
              background: 'none',
              border: 'none',
              color: 'white',
              fontSize: '1.2rem',
              cursor: 'pointer',
              marginLeft: 'auto'
            }}
          >
            ×
          </button>
        </div>
      )}

      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: '700', marginBottom: '10px' }}>
          <i className="fas fa-users" style={{ marginRight: '15px' }}></i>
          Friends & Connections
        </h1>
        <p style={{ opacity: '0.8', fontSize: '1.1rem' }}>
          Connect with other prompt engineers and collaborate
        </p>
      </div>

      {/* Search Section */}
      <div style={cardStyle}>
        <h3 style={{ marginBottom: '20px', fontSize: '1.3rem' }}>
          <i className="fas fa-search" style={{ marginRight: '10px' }}></i>
          Find Friends
        </h3>
        <div style={{ display: 'flex', gap: '15px', marginBottom: '20px' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && searchUsers()}
            placeholder="Search by email or name..."
            style={{
              flex: 1,
              padding: '12px 16px',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              background: 'rgba(255, 255, 255, 0.1)',
              color: 'white',
              fontSize: '1rem'
            }}
          />
          <button
            onClick={searchUsers}
            disabled={searching || !searchQuery.trim()}
            style={{
              ...buttonStyle('primary'),
              padding: '12px 24px',
              opacity: searching || !searchQuery.trim() ? 0.6 : 1
            }}
          >
            {searching ? (
              <>
                <i className="fas fa-spinner fa-spin" style={{ marginRight: '8px' }}></i>
                Searching...
              </>
            ) : (
              <>
                <i className="fas fa-search" style={{ marginRight: '8px' }}></i>
                Search
              </>
            )}
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '30px', flexWrap: 'wrap' }}>
        <button
          onClick={() => setActiveTab('friends')}
          style={tabStyle(activeTab === 'friends')}
        >
          <i className="fas fa-user-friends" style={{ marginRight: '8px' }}></i>
          Friends ({acceptedFriends.length})
        </button>
        <button
          onClick={() => setActiveTab('requests')}
          style={tabStyle(activeTab === 'requests')}
        >
          <i className="fas fa-user-plus" style={{ marginRight: '8px' }}></i>
          Requests ({incomingRequests.length})
        </button>
        <button
          onClick={() => setActiveTab('search')}
          style={tabStyle(activeTab === 'search')}
        >
          <i className="fas fa-search" style={{ marginRight: '8px' }}></i>
          Search Results ({searchResults.length})
        </button>
      </div>

      {/* Content based on active tab */}
      {activeTab === 'friends' && (
        <div>
          <h3 style={{ marginBottom: '20px', fontSize: '1.3rem' }}>
            My Friends ({acceptedFriends.length})
          </h3>
          
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <i className="fas fa-spinner fa-spin" style={{ fontSize: '2rem', marginBottom: '15px' }}></i>
              <p>Loading friends...</p>
            </div>
          ) : acceptedFriends.length === 0 ? (
            <div style={{
              ...cardStyle,
              textAlign: 'center',
              padding: '40px'
            }}>
              <i className="fas fa-user-friends" style={{ fontSize: '3rem', marginBottom: '15px', opacity: '0.5' }}></i>
              <h4 style={{ marginBottom: '10px' }}>No friends yet</h4>
              <p style={{ opacity: '0.8' }}>Search for other users to send friend requests!</p>
            </div>
          ) : (
            acceptedFriends.map((friend: Friend) => {
              // Determine which user is the friend based on current user ID
              const friendUser = getFriendUser(friend, currentUserId!)
              
              return (
                <div key={friend.id} style={userCardStyle}>
                  <div style={{
                    width: '50px',
                    height: '50px',
                    borderRadius: '50%',
                    background: friendUser.profile_picture 
                      ? `url(${friendUser.profile_picture})` 
                      : 'linear-gradient(45deg, #4ecdc4, #44a08d)',
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: '1.2rem'
                  }}>
                    {!friendUser.profile_picture && <i className="fas fa-user"></i>}
                  </div>
                  
                  <div style={{ flex: 1 }}>
                    <h4 style={{ marginBottom: '5px' }}>
                      {friendUser.full_name || friendUser.email}
                    </h4>
                    <p style={{ opacity: '0.8', fontSize: '0.9rem' }}>
                      {friendUser.email}
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    <Link
                      to={`/messages/${friendUser.id}`}
                      style={{
                        ...buttonStyle('primary'),
                        textDecoration: 'none',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '5px'
                      }}
                    >
                      <i className="fas fa-comment"></i>
                      Message
                    </Link>
                    <button
                      onClick={() => removeFriend(friendUser.id)}
                      style={buttonStyle('danger')}
                    >
                      <i className="fas fa-user-minus"></i>
                      Remove
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}

      {activeTab === 'requests' && (
        <div>
          <h3 style={{ marginBottom: '20px', fontSize: '1.3rem' }}>
            Friend Requests ({incomingRequests.length})
          </h3>
          
          {incomingRequests.length === 0 ? (
            <div style={{
              ...cardStyle,
              textAlign: 'center',
              padding: '40px'
            }}>
              <i className="fas fa-user-plus" style={{ fontSize: '3rem', marginBottom: '15px', opacity: '0.5' }}></i>
              <h4 style={{ marginBottom: '10px' }}>No pending requests</h4>
              <p style={{ opacity: '0.8' }}>You're all caught up!</p>
            </div>
          ) : (
            incomingRequests.map((request: Friend) => {
              const requesterUser = request.requester
              return (
                <div key={request.id} style={userCardStyle}>
                  <div style={{
                    width: '50px',
                    height: '50px',
                    borderRadius: '50%',
                    background: requesterUser.profile_picture 
                      ? `url(${requesterUser.profile_picture})` 
                      : 'linear-gradient(45deg, #4ecdc4, #44a08d)',
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: '1.2rem'
                  }}>
                    {!requesterUser.profile_picture && <i className="fas fa-user"></i>}
                  </div>
                  
                  <div style={{ flex: 1 }}>
                    <h4 style={{ marginBottom: '5px' }}>
                      {requesterUser.full_name || requesterUser.email}
                    </h4>
                    <p style={{ opacity: '0.8', fontSize: '0.9rem' }}>
                      {requesterUser.email}
                    </p>
                    <p style={{ opacity: '0.6', fontSize: '0.8rem' }}>
                      Sent {new Date(request.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      onClick={() => respondToRequest(request.requester_id, true)}
                      style={buttonStyle('primary')}
                    >
                      <i className="fas fa-check" style={{ marginRight: '5px' }}></i>
                      Accept
                    </button>
                    <button
                      onClick={() => respondToRequest(request.requester_id, false)}
                      style={buttonStyle('danger')}
                    >
                      <i className="fas fa-times" style={{ marginRight: '5px' }}></i>
                      Decline
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
  )}

  {activeTab === 'search' && (
        <div>
          <h3 style={{ marginBottom: '20px', fontSize: '1.3rem' }}>
            Search Results ({searchResults.length})
          </h3>
          
          {searchResults.length === 0 ? (
            <div style={{
              ...cardStyle,
              textAlign: 'center',
              padding: '40px'
            }}>
              <i className="fas fa-search" style={{ fontSize: '3rem', marginBottom: '15px', opacity: '0.5' }}></i>
              <h4 style={{ marginBottom: '10px' }}>No results</h4>
              <p style={{ opacity: '0.8' }}>Try searching with different keywords</p>
            </div>
          ) : (
            searchResults.map(user => (
              <div key={user.id} style={userCardStyle}>
                <div style={{
                  width: '50px',
                  height: '50px',
                  borderRadius: '50%',
                  background: user.profile_picture 
                    ? `url(${user.profile_picture})` 
                    : 'linear-gradient(45deg, #4ecdc4, #44a08d)',
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: '1.2rem'
                }}>
                  {!user.profile_picture && <i className="fas fa-user"></i>}
                </div>
                
                <div style={{ flex: 1 }}>
                  <h4 style={{ marginBottom: '5px' }}>
                    {user.display_name || user.email}
                  </h4>
                  <p style={{ opacity: '0.8', fontSize: '0.9rem' }}>
                    {user.email}
                  </p>
                  {user.school && (
                    <p style={{ opacity: '0.6', fontSize: '0.8rem' }}>
                      <i className="fas fa-graduation-cap" style={{ marginRight: '5px' }}></i>
                      {user.school}
                    </p>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  {user.is_friend ? (
                    <span style={{
                      ...buttonStyle('secondary'),
                      cursor: 'default',
                      opacity: 0.7
                    }}>
                      <i className="fas fa-check" style={{ marginRight: '5px' }}></i>
                      Friends
                    </span>
                  ) : user.has_pending_request ? (
                    <span style={{
                      ...buttonStyle('secondary'),
                      cursor: 'default',
                      opacity: 0.7
                    }}>
                      <i className="fas fa-clock" style={{ marginRight: '5px' }}></i>
                      Pending
                    </span>
                  ) : (
                    <button
                      onClick={() => sendFriendRequest(user.id)}
                      style={buttonStyle('primary')}
                    >
                      <i className="fas fa-user-plus" style={{ marginRight: '5px' }}></i>
                      Add Friend
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// Add CSS for the slide-in animation
const style = document.createElement('style')
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
`
document.head.appendChild(style)
