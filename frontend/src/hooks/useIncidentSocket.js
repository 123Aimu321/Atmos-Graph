
import {
  useEffect,
  useRef,
  useState,
} from "react";


function getWebSocketUrl() {
  const explicitUrl =
    import.meta.env.VITE_WS_URL;

  if (explicitUrl) {
    return explicitUrl;
  }

  return "ws://127.0.0.1:8000/ws/incidents";
}


export default function useIncidentSocket(
  onEvent
) {
  const [status, setStatus] =
    useState("connecting");

  const [lastEvent, setLastEvent] =
    useState(null);

  const callbackRef = useRef(onEvent);

  useEffect(() => {
    callbackRef.current = onEvent;
  }, [onEvent]);


  useEffect(() => {
    let socket = null;

    let reconnectTimer = null;

    let heartbeatTimer = null;

    let stopped = false;

    let attempt = 0;


    function clearHeartbeat() {
      if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
    }


    function connect() {
      if (stopped) return;

      setStatus("connecting");

      socket = new WebSocket(
        getWebSocketUrl()
      );


      socket.onopen = () => {
        attempt = 0;

        setStatus("connected");

        clearHeartbeat();

        heartbeatTimer = setInterval(() => {
          if (
            socket?.readyState ===
            WebSocket.OPEN
          ) {
            socket.send(
              JSON.stringify({
                type: "ping",
              })
            );
          }
        }, 25000);
      };


      socket.onmessage = (message) => {
        try {
          const event =
            JSON.parse(message.data);

          if (
            event.type === "pong" ||
            event.type ===
              "connection.established"
          ) {
            return;
          }

          setLastEvent(event);

          callbackRef.current?.(event);

        } catch (error) {
          console.warn(
            "Invalid WebSocket event:",
            error
          );
        }
      };


      socket.onerror = () => {
        setStatus("disconnected");
      };


      socket.onclose = () => {
        clearHeartbeat();

        if (stopped) return;

        setStatus("disconnected");

        attempt += 1;

        const delay = Math.min(
          1000 * 2 ** Math.min(attempt - 1, 5),
          30000
        );

        reconnectTimer = setTimeout(
          connect,
          delay
        );
      };
    }


    connect();


    return () => {
      stopped = true;

      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }

      clearHeartbeat();

      if (socket) {
        socket.close();
      }
    };

  }, []);


  return {
    status,
    lastEvent,
  };
}
