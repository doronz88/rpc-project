import time
from threading import Thread


def test_same_socket_different_threads(client):
    # get an expected result once on main thread
    expected_result = client.fs.listdir('/')

    # global to tell threads when to exit
    should_exit = False

    def listdir_thread(client):
        while not should_exit:
            assert client.fs.listdir('/') == expected_result
        return 0

    # launch the two threads
    t1 = Thread(target=listdir_thread, args=(client,))
    t2 = Thread(target=listdir_thread, args=(client,))

    t1.start()
    t2.start()

    # wait 10 seconds
    time.sleep(10)

    # tell threads they
    should_exit = True

    t1.join()
    t2.join()
